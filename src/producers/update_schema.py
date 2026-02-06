# src/producers/update_schema.py
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.error import SchemaRegistryError
from src.config.paths import FINNHUB_TRADES_AVRO_SCHEMA

def register_schema(topic_name):
    """Register the schema in the Schema Registry"""
    
    # Schema Registry configuration
    schema_registry_conf = {'url': 'http://localhost:8081'}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)
    
    # Read schema from file
    print(f"Reading schema from: {FINNHUB_TRADES_AVRO_SCHEMA}")
    with open(FINNHUB_TRADES_AVRO_SCHEMA) as f:
        avro_schema_str = f.read()
    
    # Create Schema object
    avro_schema = Schema(avro_schema_str, schema_type="AVRO")
    
    # Register in Schema Registry
    subject_name = f"{topic_name}-value"  # Use the same name as the topic
    
    try:
        schema_id = schema_registry_client.register_schema(
            subject_name=subject_name,
            schema=avro_schema
        )
        print(f"Schema registered successfully!")
        print(f"Subject: {subject_name}")
        print(f"Schema ID: {schema_id}")
        
        # Check version
        latest = schema_registry_client.get_latest_version(subject_name)
        print(f"Version: {latest.version}")
        
    except SchemaRegistryError as e:
        if "already exists" in str(e).lower():
            print(f"Schema already exists for subject '{subject_name}'")
            latest = schema_registry_client.get_latest_version(subject_name)
            print(f"Schema ID: {latest.schema_id}")
            print(f"Version: {latest.version}")
        else:
            print(f"Error registering schema: {e}")
            raise

if __name__ == "__main__":
    register_schema("trades-data")