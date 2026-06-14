# main.py
import time
import logging
import sys
from config import MODE, SYMBOL, TIMEFRAME, LEVERAGE, TP_PCT, SL_PCT, SCORE_THRESHOLD, STATE_FILE, LOG_FILE
from data.market_data import fetch_ohlcv
from signal.signal_engine import compute_signal
from execution.okx_adapter import OKXAdapter
from monitor.position_manager import PositionManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PyDROID_BOT")

def print_diagnostic(adapter):
    logger.info("=== DIAGNÓSTICO DE INICIO ===")
    ok, msg = adapter.health_check()
    logger.info(f"OKX CONNECTION ....... {'OK' if ok else 'FAIL'} - {msg}")
    diff, time_ok = adapter.check_server_time()
    logger.info(f"SERVER TIME .......... {'OK' if time_ok else 'FAIL'} (diff={diff} ms)")
    logger.info(f"SYMBOL ............... {SYMBOL}")
    logger.info(f"MODE ................. {MODE.upper()}")
    logger.info(f"LEVERAGE ............. {LEVERAGE}x")
    try:
        bal = adapter.orders.fetch_balance()
        usdt = bal.get('USDT', {}).get('free', 0)
        logger.info(f"BALANCE ACCESS ....... OK (USDT free: {usdt:.2f})")
    except Exception as e:
        logger.info(f"BALANCE ACCESS ....... FAIL ({e})")
    pos = adapter.fetch_position()
    logger.info(f"POSITION ACCESS ...... OK (posición actual: {pos if pos else 'ninguna'})")
    logger.info("=====================================")

def main():
    # Pedir credenciales si no están en entorno
    api_key = os.getenv("OKX_API_KEY")
    secret = os.getenv("OKX_SECRET")
    passphrase = os.getenv("OKX_PASSPHRASE")
    if not api_key or not secret or not passphrase:
        print("\n🔑 Ingresa tus credenciales OKX Demo:")
        api_key = input("API Key: ").strip()
        secret = input("Secret Key: ").strip()
        passphrase = input("Passphrase: ").strip()
        if not api_key or not secret or not passphrase:
            logger.error("Credenciales incompletas. Abortando.")
            sys.exit(1)
        # Opcional: guardarlas en variables de entorno para esta sesión
        os.environ["OKX_API_KEY"] = api_key
        os.environ["OKX_SECRET"] = secret
        os.environ["OKX_PASSPHRASE"] = passphrase

    logger.info(f"Iniciando PyDROID SOLANA CORE Ω en modo {MODE.upper()}")
    adapter = OKXAdapter(api_key, secret, passphrase)
    position_mgr = PositionManager(STATE_FILE)

    print_diagnostic(adapter)

    diff, time_ok = adapter.check_server_time()
    if not time_ok:
        logger.error(f"Desincronización horaria crítica: diff={diff} ms. ABORTANDO.")
        return

    ok, msg = adapter.health_check()
    if not ok:
        logger.error(f"Health check falló: {msg}. ABORTANDO.")
        return

    while True:
        try:
            # 1. Obtener datos de mercado (Binance pública)
            df_sol = fetch_ohlcv("SOL/USDT", TIMEFRAME, 200)
            df_btc = fetch_ohlcv("BTC/USDT", TIMEFRAME, 200)
            df_eth = fetch_ohlcv("ETH/USDT", TIMEFRAME, 200)
            if df_sol.empty or df_btc.empty or df_eth.empty:
                logger.warning("No se pudieron obtener datos, esperando...")
                time.sleep(60)
                continue

            # 2. Calcular señal
            signal_data = compute_signal(df_sol, df_btc, df_eth)
            logger.info(f"Señal: {signal_data['signal']}, score={signal_data['score']:.4f}")

            # 3. Verificar posición existente
            if position_mgr.has_open_position():
                pos = adapter.fetch_position()
                if pos is None:
                    logger.warning("Inconsistencia: persistencia marca posición pero exchange no. Limpiando.")
                    position_mgr.close_position()
                else:
                    logger.info(f"Posición activa detectada: {pos}. No se abre nueva.")
                    time.sleep(300)
                    continue

            # 4. Ejecutar trade si señal es válida
            if abs(signal_data["score"]) > SCORE_THRESHOLD and signal_data["signal"] != "NONE":
                current_price = df_sol["close"].iloc[-1]
                balance = adapter.orders.fetch_balance()
                usdt_balance = balance.get('USDT', {}).get('free', 0)
                if usdt_balance <= 0:
                    logger.error("Saldo insuficiente para operar.")
                    time.sleep(300)
                    continue
                contracts = (usdt_balance * LEVERAGE) / current_price
                contracts = round(contracts, 1)   # ajuste a step size de 0.1
                if contracts <= 0:
                    logger.error("Contratos calculados cero, no se opera.")
                    time.sleep(300)
                    continue

                side = "buy" if signal_data["signal"] == "LONG" else "sell"
                order = adapter.place_market_order(side, contracts)
                if not order or order.get('status') != 'closed':
                    logger.error("Error al abrir orden market")
                    continue
                entry_price = float(order['price']) if 'price' in order else current_price

                tp_pct = signal_data.get("tp_pct") if signal_data.get("tp_pct") is not None else TP_PCT
                sl_pct = signal_data.get("sl_pct") if signal_data.get("sl_pct") is not None else SL_PCT
                adapter.place_tp_sl(signal_data["signal"].lower(), contracts, entry_price, tp_pct, sl_pct)

                tp_price = entry_price * (1 + tp_pct) if signal_data["signal"] == "LONG" else entry_price * (1 - tp_pct)
                sl_price = entry_price * (1 - sl_pct) if signal_data["signal"] == "LONG" else entry_price * (1 + sl_pct)
                position_mgr.open_position(SYMBOL, signal_data["signal"].lower(), contracts, entry_price, tp_price, sl_price)
                logger.info(f"Trade ejecutado: {signal_data['signal']} {contracts} contratos @ {entry_price}")
            else:
                logger.info("No se cumplió el umbral de score o señal NONE")

            # Esperar hasta la siguiente vela de 5m
            time.sleep(300)

        except Exception as e:
            logger.exception(f"Error en ciclo principal: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
