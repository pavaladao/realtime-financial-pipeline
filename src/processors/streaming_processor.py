import os
import json
import io
import fastavro
import requests

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, LongType,
    FloatType, DoubleType, BooleanType,
    ArrayType
)

AVRO_PRIMITIVES = {
    "string": StringType(),
    "int": IntegerType(),
    "long": LongType(),
    "float": FloatType(),
    "double": DoubleType(),
    "boolean": BooleanType()
}

def avro_type_to_spark(avro_type):
    if isinstance(avro_type, list):
        non_null = [t for t in avro_type if t != "null"][0]
        return avro_type_to_spark(non_null)

    if isinstance(avro_type, str):
        if avro_type not in AVRO_PRIMITIVES:
            raise ValueError(f"Tipo Avro não suportado: {avro_type}")
        return AVRO_PRIMITIVES[avro_type]

    if isinstance(avro_type, dict):
        if avro_type["type"] == "record":
            return StructType([
                StructField(
                    f["name"],
                    avro_type_to_spark(f["type"]),
                    True
                )
                for f in avro_type["fields"]
            ])

        if avro_type["type"] == "array":
            return ArrayType(
                avro_type_to_spark(avro_type["items"])
            )

    raise ValueError(f"Tipo Avro não suportado: {avro_type}")

def avro_schema_to_spark_schema(avro_schema_json):
    schema = json.loads(avro_schema_json)
    return StructType([
        StructField(
            f["name"],
            avro_type_to_spark(f["type"]),
            True
        )
        for f in schema["fields"]
    ])

# ===== Configuration =====

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
TOPIC_NAME = os.getenv("TOPIC_NAME", "trades-data")
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "http://schema-registry:8081")

def get_schema_from_registry(topic_name, schema_registry_url):
    """
    Get the latest schema for a topic from the Schema Registry using HTTP API.
     - topic_name: name of the Kafka topic (e.g. "trades-data")
     - schema_registry_url: URL of the Schema Registry (e.g. "http://schema-registry:8081")
    """
    url = f"{schema_registry_url}/subjects/{topic_name}-value/versions/latest"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        # The answer has: {"id": 1, "subject": "...", "version": 1, "schema": "..."}
        return data["schema"]
    
    except requests.RequestException as e:
        raise RuntimeError(f"Erro ao buscar schema do Registry: {e}")

# Get the schema string
avro_schema_str = get_schema_from_registry(TOPIC_NAME, SCHEMA_REGISTRY_URL)
print(f"Schema obtido: {avro_schema_str}")

# Parse schema to Python dict (needed for fastavro)
avro_schema_dict = json.loads(avro_schema_str)

# Converts to StructType Spark
spark_schema = avro_schema_to_spark_schema(avro_schema_str)

# Create Spark Session
spark = SparkSession.builder \
    .appName("FinancialTradesStreaming") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Create deserializer UDF with schema embedded
def deserialize_avro(avro_bytes):
    """Desserializa bytes Avro usando schemaless_reader"""
    bio = io.BytesIO(avro_bytes[5:])  # Jump the 5-byte Confluent header
    return fastavro.schemaless_reader(bio, avro_schema_dict)

avro_udf = udf(deserialize_avro, spark_schema)

# Read from Kafka
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
    .option("subscribe", TOPIC_NAME) \
    .option("startingOffsets", "latest") \
    .load()

# Parse Avro and flatten
df_parsed = df.select(avro_udf(col("value")).alias("data")).select("data.*")

# Write to console
query = df_parsed.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", "false") \
    .start()

query.awaitTermination()