import json
import io
import fastavro

from confluent_kafka.schema_registry import SchemaRegistryClient
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
    # Union: ["null", "type"]
    if isinstance(avro_type, list):
        non_null = [t for t in avro_type if t != "null"][0]
        return avro_type_to_spark(non_null)

    # Primitivo
    if isinstance(avro_type, str):
        if avro_type not in AVRO_PRIMITIVES:
            raise ValueError(f"Tipo Avro não suportado: {avro_type}")
        return AVRO_PRIMITIVES[avro_type]

    # Record
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

def deserialize_avro(avro_bytes):
    """Desserializa bytes Avro em dict"""
    bio = io.BytesIO(avro_bytes[5:]) # Jump the 5-byte Confluent header
    return next(fastavro.reader(bio))

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

# -------------------------------
# Configurações Kafka + Schema Registry
# -------------------------------
KAFKA_BOOTSTRAP = "kafka:9092"
TOPIC_NAME = "trades-data"
SCHEMA_REGISTRY_URL = "http://localhost:8081"

# -------------------------------
# Retrieve the latest schema from Schema Registry
# -------------------------------

# Schema Registry setup
schema_registry_conf = {'url': SCHEMA_REGISTRY_URL}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)


# Retrieve the latest schema from Schema Registry
latest_schema = schema_registry_client.get_latest_version(f"{TOPIC_NAME}-value")
avro_schema_str = latest_schema.schema.schema_str
print(f"{avro_schema_str}")

# Converte para StructType Spark
spark_schema = avro_schema_to_spark_schema(avro_schema_str)

# -------------------------------
# Cria Spark session
# -------------------------------
spark = SparkSession.builder \
    .appName("FinancialTradesStreaming") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# -------------------------------
# UDF para desserializar Avro
# -------------------------------
avro_udf = udf(deserialize_avro, spark_schema)

# -------------------------------
# Lê stream Kafka
# -------------------------------
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
    .option("subscribe", TOPIC_NAME) \
    .option("startingOffsets", "latest") \
    .load()

# Aplica UDF e extrai colunas
df_parsed = df.select(avro_udf(col("value")).alias("data")).select("data.*")

# -------------------------------
# Sink: console (para teste)
# -------------------------------
query = df_parsed.writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

query.awaitTermination()
