# main.py
import time
import logging
import sys
from datetime import datetime

from config import (
    MODE, ASSETS, TIMEFRAME, RISK_PER_TRADE, MAX_LEVERAGE,
    SCORE_THRESHOLD, TRADE_HOURS_START, TRADE_HOURS_END,
    STATE_FILE, LOG_FILE, API_KEY, SECRET_KEY, PASSPHRASE
)
from data.market_data import fetch_ohlcv
from signal.signal_engine import compute_signal_for_asset
from execution.okx_adapter import OKXAdapter
from monitor.position_manager import PositionManager
from risk.position_sizing import calculate_contracts
from utils.precision import get_step_size

# --- Configuración del sistema de logs ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PideltaBot")

# ============================================================================
#                           FUNCIONES AUXILIARES
# ============================================================================

def fetch_all_data(assets, timeframe, limit=200):
    """Descarga datos históricos de todos los activos desde Binance."""
    data = {}
    for asset in assets:
        # Se convierte el símbolo de OKX al formato de Binance
        binance_sym = asset.replace(':USDT', '')
        data[asset] = fetch_ohlcv(binance_sym, timeframe, limit)
    return data

def compute_all_signals(data, assets):
    """Calcula la señal para cada activo de la lista usando BTC y ETH como macro."""
    # Datos de BTC y ETH necesarios para el filtro macro de todos los activos
    btc_data = data.get("BTC/USDT:USDT")
    eth_data = data.get("ETH/USDT:USDT")
    if btc_data is None or eth_data is None or btc_data.empty or eth_data.empty:
        return {}

    signals = {}
    for asset in assets:
        self_data = data.get(asset)
        if self_data is None or self_data.empty:
            continue
        signals[asset] = compute_signal_for_asset(asset, self_data, btc_data, eth_data)
    return signals

def select_best_signal(signals):
    """Selecciona el activo con la señal de mayor intensidad (abs(score))."""
    best = None
    best_abs = -1.0
    for asset, sig in signals.items():
        if sig['signal'] != 'none' and abs(sig['score']) > best_abs:
            best_abs = abs(sig['score'])
            best = sig
    return best

def print_startup_diagnostic(adapter):
    """Muestra un diagnóstico del sistema y la conexión con OKX al iniciar."""
    logger.info("=== DIAGNÓSTICO DE INICIO ===")
    ok, msg = adapter.health_check()
    logger.info(f"OKX CONNECTION ....... {'OK' if ok else 'FAIL'} - {msg}")
    diff, time_ok = adapter.check_server_time()
    logger.info(f"SERVER TIME .......... {'OK' if time_ok else 'FAIL'} (diff={diff} ms)")
    logger.info(f"ASSETS ............... {ASSETS}")
    logger.info(f"MODE ................. {MODE.upper()}")
    logger.info(f"MAX LEVERAGE ......... {MAX_LEVERAGE}x")
    logger.info(f"RISK PER TRADE ....... {RISK_PER_TRADE*100:.1f}%")
    logger.info(f"TRADE HOURS .......... {TRADE_HOURS_START}:00-{TRADE_HOURS_END}:00 UTC")
    try:
        bal = adapter.orders.fetch_balance()
        usdt = bal.get('USDT', {}).get('free', 0)
        logger.info(f"BALANCE ACCESS ....... OK (USDT free: {usdt:.2f})")
    except Exception as e:
        logger.info(f"BALANCE ACCESS ....... FAIL ({e})")
    logger.info("=====================================")

# ============================================================================
#                               BUCLE PRINCIPAL
# ============================================================================

def main():
    # --- Obtención de credenciales ---
    api_key = API_KEY
    secret = SECRET_KEY
    passphrase = PASSPHRASE
    if not api_key or not secret or not passphrase:
        print("\n🔑 OKX Demo credentials required:")
        api_key = input("API Key: ").strip()
        secret = input("Secret Key: ").strip()
        passphrase = input("Passphrase: ").strip()
        if not api_key or not secret or not passphrase:
            logger.error("Credenciales incompletas. Abortando.")
            sys.exit(1)

    # --- Inicialización de componentes ---
    adapter = OKXAdapter(api_key, secret, passphrase)
    pos_mgr = PositionManager(STATE_FILE)

    # --- Diagnóstico y comprobaciones iniciales ---
    print_startup_diagnostic(adapter)

    # Comprobación de la sincronización horaria
    diff, time_ok = adapter.check_server_time()
    if not time_ok:
        logger.error(f"Desincronización horaria crítica: diff={diff} ms. ABORTANDO.")
        return

    ok, msg = adapter.health_check()
    if not ok:
        logger.error(f"Health check falló: {msg}. ABORTANDO.")
        return

    # --- Configuración inicial de los símbolos en OKX ---
    for asset in ASSETS:
        try:
            adapter.setup_symbol(asset, MAX_LEVERAGE)
            logger.info(f"Símbolo {asset} configurado: margen aislado, {MAX_LEVERAGE}x.")
        except Exception as e:
            logger.warning(f"No se pudo configurar {asset}: {e}")

    # --- Bucle infinito de trading ---
    while True:
        try:
            # 1. Filtro de horario (solo opera dentro de la ventana configurada)
            current_hour = datetime.utcnow().hour
            if not (TRADE_HOURS_START <= current_hour < TRADE_HOURS_END):
                logger.info("Fuera de la ventana de trading. Esperando...")
                time.sleep(300)
                continue

            # 2. Obtención de datos históricos de Binance
            data = fetch_all_data(ASSETS, TIMEFRAME, limit=200)
            if not data:
                logger.warning("No se pudieron obtener los datos. Reintentando...")
                time.sleep(60)
                continue

            # 3. Cálculo de señales para todos los activos
            signals = compute_all_signals(data, ASSETS)
            if not signals:
                logger.warning("No se generaron señales válidas. Reintentando...")
                time.sleep(60)
                continue

            # 4. Selección del activo con la mejor señal
            best_signal = select_best_signal(signals)
            if not best_signal:
                logger.info("No hay activo con señal que supere el umbral.")
                time.sleep(60)
                continue

            asset = best_signal['asset']
            signal = best_signal['signal']   # 'long' or 'short'
            score = best_signal['score']
            atr = best_signal['atr']

            logger.info(f"Mejor activo: {asset} | Señal: {signal} | Score: {score:.4f} | ATR: {atr:.4f}")

            # 5. Verificación de posición abierta (persistencia)
            if pos_mgr.has_open_position():
                live_pos = adapter.fetch_position(asset)
                if live_pos is None:
                    logger.warning("Inconsistencia de estado: limpiando estado persistente...")
                    pos_mgr.close_position()
                else:
                    logger.info("Ya hay una posición activa. No se abre una nueva.")
                    time.sleep(60)
                    continue

            # 6. Obtención de datos de mercado y balance para el dimensionamiento
            ticker = adapter.orders.exchange.fetch_ticker(asset)
            current_price = ticker['last']
            balance = adapter.orders.fetch_balance()
            equity = balance.get('USDT', {}).get('free', 0)

            if equity <= 0:
                logger.error("Saldo insuficiente en USDT.")
                time.sleep(300)
                continue

            # 7. Cálculo de precios de Stop Loss (fundamental para el dimensionamiento)
            if signal == 'long':
                sl_price = current_price - SL_ATR_MULT * atr
            else:
                sl_price = current_price + SL_ATR_MULT * atr

            # 8. Dimensionamiento de la posición basado en el riesgo
            contracts = calculate_contracts(
                adapter.orders.exchange, asset, equity, RISK_PER_TRADE,
                current_price, sl_price, MAX_LEVERAGE
            )
            if contracts <= 0:
                logger.error("El número de contratos calculado es inválido. Cancelando operación.")
                time.sleep(60)
                continue

            # 9. Ejecución de la orden de mercado
            side = "buy" if signal == "long" else "sell"
            order = adapter.open_position(asset, side, contracts)
            if not order or order.get('status') not in ('closed', 'open'):
                logger.error("Fallo en la ejecución de la orden de mercado.")
                continue

            entry_price = float(order.get('price', current_price))
            logger.info(f"Posición abierta: {signal} {contracts} contratos de {asset} @ {entry_price}")

            # 10. Colocación de las órdenes de Take Profit y Stop Loss
            tp_price = entry_price + TP_ATR_MULT * atr if signal == 'long' else entry_price - TP_ATR_MULT * atr
            adapter.set_tp_sl(asset, signal, contracts, entry_price, atr)

            # 11. Persistencia del estado de la posición
            pos_mgr.open_position(asset, signal, contracts, entry_price, tp_price, sl_price, atr)

            # 12. Pausa de 5 minutos antes del siguiente ciclo
            time.sleep(300)

        except Exception as e:
            logger.exception(f"Error en el bucle principal del bot: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
