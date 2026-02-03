import websocket
import os
from dotenv import load_dotenv
import json

load_dotenv(".env")

AUTH_TOKEN = os.getenv("FINNHUB_TOKEN")
MAX_MESSAGES = 100
message_count = 0
buffer = []

def on_message(ws, message):
    global message_count
    global buffer

    buffer.append(message)

    message_count += 1

    if message_count >= MAX_MESSAGES:
        ws.close()

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    ws.send('{"type":"subscribe","symbol":"AAPL"}')
    ws.send('{"type":"subscribe","symbol":"AMZN"}')
    ws.send('{"type":"subscribe","symbol":"BINANCE:BTCUSDT"}')
    ws.send('{"type":"subscribe","symbol":"IC MARKETS:1"}')

if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(f"wss://ws.finnhub.io?token={AUTH_TOKEN}",
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()