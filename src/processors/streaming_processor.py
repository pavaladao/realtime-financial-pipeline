import os
import json
import io
import fastavro
import requests
import logging
import time
from typing import Optional, Dict, Any
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, LongType,
    FloatType, DoubleType, BooleanType,
    ArrayType
)

#region KafkaReader

logger = logging.getLogger(__name__)

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

        # Create UDF
        self._avro_udf = self._build_avro_udf()

        # DataFrame will be created lazily
        self._df_stream = None
        self._query = None

    @staticmethod
    def _create_spark_session() -> SparkSession:
        """Creates a default SparkSession."""
        return SparkSession.builder \
            .appName("KafkaReaderApp") \
            .master("spark://spark-master:7077") \
            .getOrCreate()

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
        try:
            bio = io.BytesIO(avro_bytes[5:])  # Remove Confluent header
            return fastavro.schemaless_reader(bio, self.avro_schema_dict)
        except Exception as e:
            logger.error(f"Error deserializing Avro: {e}")
            raise

    def _build_avro_udf(self):
        """Creates the UDF without capturing self."""
        avro_schema_dict = self.avro_schema_dict  # pure schema dict
        spark_schema = self.spark_schema

        def deserialize_avro(avro_bytes: bytes):
            import io
            import fastavro
            try:
                bio = io.BytesIO(avro_bytes[5:])  # Remove Confluent header
                return fastavro.schemaless_reader(bio, avro_schema_dict)
            except Exception as e:
                return None

        return udf(deserialize_avro, spark_schema)

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

#endregion

from pyspark.sql.functions import (
    to_timestamp, udf, col, explode, window,
    sum, avg, min, max, count, stddev
)

if __name__ == "__main__":

    reader = KafkaReader(
        kafka_bootstrap="kafka:29092",
        topic="trades-data",
        schema_registry_url="http://schema-registry:8081"
    )

    reader.spark.sparkContext.setLogLevel("ERROR")

    df = reader.get_stream()

    df_trades = df \
        .filter(col("type") == "trade") \
        .select(explode(col("data")).alias("trade")) \
        .select(
            col("trade.s").alias("symbol"),
            col("trade.p").alias("price"),
            col("trade.v").alias("volume"),
            to_timestamp((col("trade.t") / 1000)).alias("event_time")
        )

    # ── 1-minute tumbling window ────────────────────────────────
    df_1min = df_trades \
        .withWatermark("event_time", "10 seconds") \
        .groupBy(window("event_time", "1 minute"), col("symbol")) \
        .agg(
            sum("volume").alias("total_volume"),
            avg("price").alias("avg_price"),
            min("price").alias("min_price"),
            max("price").alias("max_price"),
            count("*").alias("trade_count"),
            stddev("price").alias("volatility"),
            sum(col("price") * col("volume")).alias("_pv_sum")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "symbol", "total_volume", "avg_price",
            "min_price", "max_price", "trade_count", "volatility",
            (col("_pv_sum") / col("total_volume")).alias("vwap")
        )

    #  ── 5-minute sliding window (1-min slide) ───────────────────
    df_5min = df_trades \
        .withWatermark("event_time", "30 seconds") \
        .groupBy(window("event_time", "5 minutes", "1 minute"), col("symbol")) \
        .agg(
            sum("volume").alias("total_volume"),
            avg("price").alias("avg_price"),
            stddev("price").alias("volatility"),
            sum(col("price") * col("volume")).alias("_pv_sum")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "symbol", "total_volume", "avg_price", "volatility",
            (col("_pv_sum") / col("total_volume")).alias("vwap")
        )

    # ── Anomaly detection via foreachBatch ───────────────────────
    def detect_anomalies(batch_df, batch_id):
        if batch_df.isEmpty():
            return

        avg_vol = batch_df \
            .groupBy("symbol") \
            .agg(avg("total_volume").alias("avg_volume"))

        anomalies = batch_df \
            .join(avg_vol, on="symbol") \
            .filter(col("total_volume") > col("avg_volume") * 3.0) \
            .select("symbol", "window_start", "total_volume", "avg_volume")

        if not anomalies.isEmpty():
            print(f"\n🚨 ANOMALY DETECTED (batch {batch_id}):")
            anomalies.show(truncate=False)

    # ── Write to PostgreSQL ─────────────────────────────────────────

    POSTGRES_URL = f"jdbc:postgresql://postgres:5432/{os.getenv('POSTGRES_DB')}"
    POSTGRES_PROPS = {
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "driver": "org.postgresql.Driver"
    }

    def write_to_postgres(table: str):
        """Returns a function to write each batch to a specific PostgreSQL table."""
        def _write(batch_df, batch_id):
            if batch_df.isEmpty():
                print(f"⏳ Batch {batch_id} — empty, waiting for window to close...")
                return
            batch_df.write \
                .format("jdbc") \
                .option("url", POSTGRES_URL) \
                .option("dbtable", table) \
                .option("user", POSTGRES_PROPS["user"]) \
                .option("password", POSTGRES_PROPS["password"]) \
                .option("driver", POSTGRES_PROPS["driver"]) \
                .mode("append") \
                .save()
            print(f"✓ Batch {batch_id} written to PostgreSQL table '{table}'")
        return _write

    def write_anomalies(batch_df, batch_id):
        if batch_df.isEmpty():
            return

        avg_vol = batch_df.groupBy("symbol") \
            .agg(avg("total_volume").alias("avg_volume"))

        anomalies = batch_df \
            .join(avg_vol, on="symbol") \
            .filter(col("total_volume") > col("avg_volume") * 3.0) \
            .withColumn("ratio", col("total_volume") / col("avg_volume")) \
            .select(
                "symbol", "window_start", "window_end",
                "total_volume", "avg_volume", "ratio",
                "avg_price", "vwap"
            )

        if not anomalies.isEmpty():
            anomalies.write \
                .format("jdbc") \
                .option("url", POSTGRES_URL) \
                .option("dbtable", "anomalies") \
                .option("user", POSTGRES_PROPS["user"]) \
                .option("password", POSTGRES_PROPS["password"]) \
                .option("driver", POSTGRES_PROPS["driver"]) \
                .mode("append") \
                .save()
            print(f"🚨 {anomalies.count()} anomaly(ies) detected in batch {batch_id}")

    # ── Queries ──────────────────────────────────────────────────
    q1 = df_1min.writeStream \
        .foreachBatch(write_to_postgres("trades_aggregated_1min")) \
        .outputMode("append") \
        .start()

    q2 = df_5min.writeStream \
        .foreachBatch(write_to_postgres("trades_aggregated_5min")) \
        .outputMode("append") \
        .start()

    q3 = df_1min.writeStream \
        .foreachBatch(write_anomalies) \
        .outputMode("append") \
        .start()

    reader.spark.streams.awaitAnyTermination()