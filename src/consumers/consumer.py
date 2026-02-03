from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer

# Schema Registry configuration
schema_registry_conf = {'url': 'http://localhost:8081'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

# Avro deserializer
avro_deserializer = AvroDeserializer(schema_registry_client)

# Kafka configuration
consumer_config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'financial_data',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False
}

consumer = Consumer(consumer_config)
topics = ["financial_data"]
consumer.subscribe(topics)

batch = []

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
                data = avro_deserializer(msg.value(), None)
                
                if data is None:
                    print("Received message but failed deserialization")
                    continue

            except Exception as e:
                print(f"Deserialization/validation error: {e}")
                continue

            # Manual commit
            consumer.commit()

            print(f"Received message: {data}")
            batch.append(data)

    except KeyboardInterrupt:
        print("Shutting down consumer...")
    finally:
        consumer.close()
