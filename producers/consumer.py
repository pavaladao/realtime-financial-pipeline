from confluent_kafka import Consumer, KafkaError
import json
from jsonschema import validate, ValidationError

consumer_config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'financial_data',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False
}

consumer = Consumer(consumer_config)

subscribe_topics = ["financial_data"]

consumer.subscribe(subscribe_topics)

print(f"Subscribed to topics: {subscribe_topics}")

batch = []

with open('./finnhub_trades_schema.json') as schema_file:
    validation_schema = json.load(schema_file)

if __name__ == "__main__":
    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                print("No message received yet...")
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"Error: {msg.error()}")
                    break
            
            try:
                data = json.loads(msg.value().decode('utf-8'))
                validate(instance=data, schema=validation_schema)

            except ValidationError as ve:

                print(f"Validation error: {ve.message}")
                continue

            consumer.commit()

            print(f'Received message: {data}')
            
            batch.append(data)

    except KeyboardInterrupt:
        print("Shutting down consumer...")
    except Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        consumer.close()

