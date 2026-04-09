import os
import sys
import json
import io
import fastavro
import requests
import logging
from typing import Optional, Dict, Any
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import udf, col
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, LongType,
    FloatType, DoubleType, BooleanType,
    ArrayType
)

logger = logging.getLogger(__name__)

# Repo root so `import src` works on executors when UDFs are unpickled (same path as Docker /app).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def _deserialize_avro_bytes(avro_bytes: bytes, avro_schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Deserialize Confluent wire-format Avro payload (5-byte header + payload)."""
    try:
        bio = io.BytesIO(avro_bytes[5:])
        return fastavro.schemaless_reader(bio, avro_schema_dict)
    except Exception as e:
        logger.error(f"Error deserializing Avro: {e}")
        raise


def _avro_udf_from_schema(avro_schema_dict: Dict[str, Any], spark_schema: StructType):
    """
    Build a UDF that only closes over picklable data (schema dict), not SparkSession.

    Binding ``udf(self._deserialize_avro, ...)`` pickles ``KafkaReader`` and fails on
    workers with CONTEXT_ONLY_VALID_ON_DRIVER (SPARK-5063).
    """

    def _deserialize(avro_bytes: bytes) -> Dict[str, Any]:
        return _deserialize_avro_bytes(avro_bytes, avro_schema_dict)

    return udf(_deserialize, spark_schema)


class KafkaReader:
    """
    Kafka stream reader with Avro support via Schema Registry.

    Abstracts all the complexity of deserialization and schema management.
    Returns DataFrames ready to be processed.

    Example:
        reader = KafkaReader(
            kafka_bootstrap="kafka:29092",
            topic="trades-data",
            schema_registry_url="http://schema-registry:8081"
        )

        df = reader.get_stream()
        query = df.writeStream.format("console").start()
        query.awaitTermination()
    """

    # Mapping of Avro types to Spark types
    AVRO_PRIMITIVES = {
        "string": StringType(),
        "int": IntegerType(),
        "long": LongType(),
        "float": FloatType(),
        "double": DoubleType(),
        "boolean": BooleanType()
    }

    def __init__(
        self,
        kafka_bootstrap: str,
        topic: str,
        schema_registry_url: str,
        spark: Optional[SparkSession] = None,
        starting_offset: str = "latest"
    ):
        """
        Initializes the Kafka reader.

        Args:
            kafka_bootstrap: Kafka address (e.g. "kafka:29092")
            topic: Kafka topic name (e.g. "trades-data")
            schema_registry_url: Schema Registry URL (e.g. "http://schema-registry:8081")
            spark: SparkSession (creates a new one if not provided)
            starting_offset: "latest" or "earliest"
        """
        self.kafka_bootstrap = kafka_bootstrap
        self.topic = topic
        self.schema_registry_url = schema_registry_url
        self.starting_offset = starting_offset

        # Initialize Spark if not provided
        self.spark = spark or self._create_spark_session()

        # Load schema
        logger.info(f"Loading schema for topic '{topic}' from Registry...")
        self.avro_schema_str = self._fetch_schema_from_registry()
        self.avro_schema_dict = json.loads(self.avro_schema_str)
        logger.info("✓ Schema loaded successfully")

        # Convert to Spark schema
        self.spark_schema = self._avro_schema_to_spark_schema(self.avro_schema_str)

        # UDF must not close over self (contains SparkSession / SparkContext).
        self._avro_udf = _avro_udf_from_schema(self.avro_schema_dict, self.spark_schema)

        # DataFrame will be created lazily
        self._df_stream = None
        self._query = None

    @staticmethod
    def _create_spark_session() -> SparkSession:
        """Creates a default SparkSession."""
        if _REPO_ROOT not in sys.path:
            sys.path.insert(0, _REPO_ROOT)
        py_path = os.environ.get("PYTHONPATH", "")
        executor_pythonpath = (
            f"{_REPO_ROOT}{os.pathsep}{py_path}" if py_path else _REPO_ROOT
        )
        return (
            SparkSession.builder.appName("KafkaReaderApp")
            .master("spark://spark-master:7077")
            .config("spark.executorEnv.PYTHONPATH", executor_pythonpath)
            .getOrCreate()
        )

    def _fetch_schema_from_registry(self) -> str:
        """
        Fetches the latest schema from Schema Registry.

        Returns:
            Avro schema JSON string

        Raises:
            RuntimeError: If the schema cannot be fetched
        """
        url = f"{self.schema_registry_url}/subjects/{self.topic}-value/versions/latest"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data["schema"]

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"❌ Error: Could not connect to Schema Registry at {self.schema_registry_url}\n"
                f"   Check if Schema Registry is running."
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise RuntimeError(
                    f"❌ Error: Schema not found for topic '{self.topic}'\n"
                    f"   Check if the topic and schema exist in the Registry."
                )
            raise RuntimeError(f"❌ HTTP Error {e.response.status_code}: {e}")
        except requests.RequestException as e:
            raise RuntimeError(f"❌ Error fetching schema: {e}")

    @staticmethod
    def _avro_type_to_spark(avro_type: Any) -> Any:
        """Converts an Avro type to a Spark type."""
        # List (union types like ["null", "string"])
        if isinstance(avro_type, list):
            non_null = [t for t in avro_type if t != "null"][0]
            return KafkaReader._avro_type_to_spark(non_null)

        # Primitive type
        if isinstance(avro_type, str):
            if avro_type not in KafkaReader.AVRO_PRIMITIVES:
                raise ValueError(f"Unsupported Avro type: {avro_type}")
            return KafkaReader.AVRO_PRIMITIVES[avro_type]

        # Complex type
        if isinstance(avro_type, dict):
            if avro_type["type"] == "record":
                return StructType([
                    StructField(
                        f["name"],
                        KafkaReader._avro_type_to_spark(f["type"]),
                        True
                    )
                    for f in avro_type["fields"]
                ])

            if avro_type["type"] == "array":
                return ArrayType(
                    KafkaReader._avro_type_to_spark(avro_type["items"])
                )

        raise ValueError(f"Unsupported Avro type: {avro_type}")

    def _avro_schema_to_spark_schema(self, avro_schema_json: str) -> StructType:
        """Converts an Avro schema (JSON string) to a Spark StructType."""
        schema = json.loads(avro_schema_json)
        return StructType([
            StructField(
                f["name"],
                self._avro_type_to_spark(f["type"]),
                True
            )
            for f in schema["fields"]
        ])

    def _deserialize_avro(self, avro_bytes: bytes) -> Dict[str, Any]:
        """
        Deserializes Avro bytes using the schema.

        Removes the 5-byte Confluent header and deserializes the payload.
        """
        return _deserialize_avro_bytes(avro_bytes, self.avro_schema_dict)

    def get_stream(self) -> DataFrame:
        """
        Returns the parsed streaming DataFrame ready for processing.

        Returns:
            DataFrame with deserialized Kafka data

        Example:
            df = reader.get_stream()
            df_filtered = df.filter(df['price'] > 100)
            df_filtered.writeStream.format("console").start()
        """
        if self._df_stream is None:
            logger.info(
                f"Connecting to Kafka ({self.kafka_bootstrap}, topic: {self.topic})..."
            )

            # Read from Kafka
            df_raw = self.spark.readStream \
                .format("kafka") \
                .option("kafka.bootstrap.servers", self.kafka_bootstrap) \
                .option("subscribe", self.topic) \
                .option("startingOffsets", self.starting_offset) \
                .load()

            # Deserialize Avro
            self._df_stream = df_raw.select(
                self._avro_udf(col("value")).alias("data")
            ).select("data.*")

            logger.info("✓ Stream connected and parsed successfully")

        return self._df_stream

    def start_streaming(
        self,
        output_format: str = "console",
        output_mode: str = "append",
        **options
    ) -> Any:
        """
        Starts streaming to a specific sink.

        Args:
            output_format: "console", "parquet", "kafka", "jdbc", etc
            output_mode: "append", "update", "complete"
            **options: Sink-specific options

        Returns:
            StreamingQuery to control the streaming

        Examples:
            # Console
            query = reader.start_streaming(output_format="console")

            # Parquet
            query = reader.start_streaming(
                output_format="parquet",
                path="/data/trades",
                checkpointLocation="/data/_checkpoint"
            )

            # Kafka
            query = reader.start_streaming(
                output_format="kafka",
                kafka_bootstrap_servers="kafka:29092",
                topic="output-topic",
                checkpointLocation="/data/_checkpoint"
            )
        """
        df = self.get_stream()

        query = df.writeStream \
            .format(output_format) \
            .outputMode(output_mode)

        # Add options
        for key, value in options.items():
            query = query.option(key, value)

        self._query = query.start()
        logger.info(f"✓ Streaming started on {output_format}")

        return self._query

    def stop(self):
        """Stops the streaming."""
        if self._query is not None:
            self._query.stop()
            logger.info("✓ Streaming stopped")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

# ============================================================
# Usage example
# ============================================================

if __name__ == "__main__":
    import logging

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create reader
    reader = KafkaReader(
        kafka_bootstrap=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"),
        topic=os.getenv("TOPIC_NAME", "trades-data"),
        schema_registry_url=os.getenv(
            "SCHEMA_REGISTRY_URL",
            "http://schema-registry:8081"
        )
    )

    # Option 1: Simple (console)
    df = reader.get_stream()
    query = reader.start_streaming(
        output_format="console",
        truncate="false"
    )
    query.awaitTermination()

    # Option 2: With processing
    # df = reader.get_stream()
    # df_filtered = df.filter(df['price'] > 100)
    # query = df_filtered.writeStream.format("console").start()
    # query.awaitTermination()

    # Option 3: With foreach (custom processing)
    # def process_batch(batch_df, batch_id):
    #     print(f"\n=== Batch {batch_id} ===")
    #     batch_df.show()
    #
    # df = reader.get_stream()
    # query = df.writeStream.foreachBatch(process_batch).start()
    # query.awaitTermination()
