import websocket
import json
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField
from src.config.paths import FINNHUB_TRADES_AVRO_SCHEMA
from src.config.env import FINNHUB_TOKEN

MAX_MESSAGES = 10
message_count = 0

# Schema Registry setup
schema_registry_conf = {'url': 'http://localhost:8081'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

# Load Avro schema
with open(FINNHUB_TRADES_AVRO_SCHEMA) as schema_file:
    avro_schema_str = schema_file.read()
    
avro_serializer = AvroSerializer(
    schema_registry_client,
    avro_schema_str,
    lambda obj, ctx: obj
)

# Kafka Producer setup
producer_config = {'bootstrap.servers': 'localhost:9092'}
producer = Producer(producer_config)

# WebSocket and topic setup
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

    msg_data = json.loads(message)

    serialized_value = avro_serializer(
        msg_data,
        SerializationContext(topic_name, MessageField.VALUE)
    )

    producer.produce(
        topic=topic_name,
        value=serialized_value,
        callback=delivery_report,
        
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
        f"wss://ws.finnhub.io?token={FINNHUB_TOKEN}",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open

    try:
        ws.run_forever()
    finally:
        producer.flush()
