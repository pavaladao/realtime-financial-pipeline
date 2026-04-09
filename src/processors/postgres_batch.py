"""PostgreSQL foreachBatch writers for Structured Streaming."""

import os

from pyspark.sql.functions import avg, col


def load_jdbc_settings_from_env():
    """JDBC URL and options from POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD."""
    db = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    pw = os.getenv("POSTGRES_PASSWORD")
    if not db or not user or not pw:
        raise RuntimeError(
            "Set POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD (non-empty). "
            "In Docker, they must match the postgres service; if you changed the password "
            "after the DB was first created, recreate the volume or ALTER USER."
        )
    url = f"jdbc:postgresql://postgres:5432/{db}"
    props = {
        "user": user,
        "password": pw,
        "driver": "org.postgresql.Driver",
    }
    return url, props


def make_table_foreach_batch(table: str):
    """Returns a foreachBatch callable that appends each batch to the given table."""

    url, props = load_jdbc_settings_from_env()

    def _write(batch_df, batch_id):
        if batch_df.isEmpty():
            print(
                f"⏳ Batch {batch_id} — empty, waiting for window to close...",
                flush=True,
            )
            return
        (
            batch_df.write.format("jdbc")
            .option("url", url)
            .option("dbtable", table)
            .option("user", props["user"])
            .option("password", props["password"])
            .option("driver", props["driver"])
            .mode("append")
            .save()
        )
        print(
            f"✓ Batch {batch_id} written to PostgreSQL table '{table}'",
            flush=True,
        )

    return _write


def make_anomaly_foreach_batch():
    """foreachBatch that detects volume spikes vs batch mean per symbol and writes anomalies."""

    url, props = load_jdbc_settings_from_env()

    def write_anomalies(batch_df, batch_id):
        if batch_df.isEmpty():
            return

        avg_vol = batch_df.groupBy("symbol").agg(avg("total_volume").alias("avg_volume"))

        anomalies = (
            batch_df.join(avg_vol, on="symbol")
            .filter(col("total_volume") > col("avg_volume") * 3.0)
            .withColumn("ratio", col("total_volume") / col("avg_volume"))
            .select(
                "symbol",
                "window_start",
                "window_end",
                "total_volume",
                "avg_volume",
                "ratio",
                "avg_price",
                "vwap",
            )
        )

        if not anomalies.isEmpty():
            (
                anomalies.write.format("jdbc")
                .option("url", url)
                .option("dbtable", "anomalies")
                .option("user", props["user"])
                .option("password", props["password"])
                .option("driver", props["driver"])
                .mode("append")
                .save()
            )
            print(
                f"🚨 {anomalies.count()} anomaly(ies) detected in batch {batch_id}",
                flush=True,
            )

    return write_anomalies
