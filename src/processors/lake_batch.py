"""S3A (MinIO / AWS) foreachBatch writers for raw bronze Parquet in Structured Streaming."""

import os
from typing import Optional, Tuple

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, dayofmonth, hour, month, year


def is_lake_enabled() -> bool:
    """True when LAKE_ENABLED is a truthy string (1, true, yes, on)."""
    v = os.getenv("LAKE_ENABLED", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def infer_ssl_and_path_style(endpoint: Optional[str]) -> Tuple[bool, bool]:
    """
    Returns (connection_ssl_enabled, path_style_access).
    No endpoint => AWS virtual-hosted endpoints, SSL on.
    Custom endpoint (e.g. MinIO) => path-style, SSL only if https.
    """
    ep = (endpoint or "").strip()
    if not ep:
        return True, False
    return ep.lower().startswith("https"), True


def load_s3a_settings_from_env():
    """
    Bucket, optional endpoint, and credentials for S3A.
    Raises if required variables are missing (when validating for lake writes).
    """
    bucket = os.getenv("S3A_BUCKET", "").strip()
    endpoint = os.getenv("S3A_ENDPOINT", "").strip() or None
    access = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    if not bucket or not access or not secret:
        raise RuntimeError(
            "Lake storage requires S3A_BUCKET, AWS_ACCESS_KEY_ID, and "
            "AWS_SECRET_ACCESS_KEY (non-empty). For MinIO set S3A_ENDPOINT, e.g. "
            "http://minio:9000"
        )
    return bucket, endpoint, access, secret


def trades_raw_base_uri(bucket: str) -> str:
    """Bronze prefix for exploded trades (Parquet)."""
    return f"s3a://{bucket}/trades_raw"


def apply_s3a_hadoop_conf(spark: SparkSession) -> None:
    """Configure Hadoop S3A on the driver; propagates to executors for this SparkContext."""
    _bucket, endpoint, access, secret = load_s3a_settings_from_env()
    had = spark.sparkContext._jsc.hadoopConfiguration()

    had.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    had.set("fs.s3a.access.key", access)
    had.set("fs.s3a.secret.key", secret)

    ssl, path_style = infer_ssl_and_path_style(endpoint)
    had.set("fs.s3a.path.style.access", "true" if path_style else "false")
    had.set("fs.s3a.connection.ssl.enabled", "true" if ssl else "false")
    if endpoint:
        had.set("fs.s3a.endpoint", endpoint)


def make_raw_trades_parquet_foreach_batch():
    """
    Returns a foreachBatch callable that appends each batch as Snappy Parquet under
    s3a://<bucket>/trades_raw, partitioned by year/month/day/hour from event_time.
    """

    bucket, _endpoint, _access, _secret = load_s3a_settings_from_env()
    base_path = trades_raw_base_uri(bucket)

    def _write(batch_df, batch_id):
        n = batch_df.count()
        if n == 0:
            print(
                f"⏳ Lake batch {batch_id} — empty, skipping Parquet write...",
                flush=True,
            )
            return
        out = (
            batch_df.withColumn("year", year(col("event_time")))
            .withColumn("month", month(col("event_time")))
            .withColumn("day", dayofmonth(col("event_time")))
            .withColumn("hour", hour(col("event_time")))
        )
        (
            out.write.mode("append")
            .format("parquet")
            .option("compression", "snappy")
            .partitionBy("year", "month", "day", "hour")
            .save(base_path)
        )
        print(
            f"✓ Lake batch {batch_id} — wrote {n} row(s) to {base_path}",
            flush=True,
        )

    return _write
