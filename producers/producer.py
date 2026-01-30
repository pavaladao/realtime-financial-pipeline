import websocket
import os
from dotenv import load_dotenv
import json
from confluent_kafka import Producer

load_dotenv()
AUTH_TOKEN = os.getenv("FINNHUB_TOKEN")

MAX_MESSAGES = 10
message_count = 0

producer_config = {'bootstrap.servers': 'localhost:9092'}
producer = Producer(producer_config)

tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'BINANCE:BTCUSDT']
topic_name = "financial_data"

def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

def on_message(ws, message):
    global message_count
    message_count += 1

    producer.produce(
        topic=topic_name,
        value=message.encode('utf-8'),
        callback=delivery_report
    )
    producer.poll(0)

    if message_count >= MAX_MESSAGES:
        ws.close()

def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print(f"### closed ### code={close_status_code}, msg={close_msg}")
    producer.flush()

def on_open(ws):
    for symbol in tickers:
        ws.send(json.dumps({"type":"subscribe","symbol":symbol}))

if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={AUTH_TOKEN}",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open

    try:
        ws.run_forever()
    finally:
        producer.flush()
