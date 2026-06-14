# execution/okx_auth.py
import time
import base64
import hmac
import json

def generate_timestamp():
    return str(int(time.time() * 1000))

def generate_signature(timestamp, method, request_path, body, secret_key):
    if body is None:
        body = ""
    else:
        body = json.dumps(body)
    message = timestamp + method.upper() + request_path + body
    mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    return base64.b64encode(mac.digest()).decode('utf-8')

def build_headers(api_key, secret_key, passphrase, timestamp, method, request_path, body=None):
    sign = generate_signature(timestamp, method, request_path, body, secret_key)
    return {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json"
    }
