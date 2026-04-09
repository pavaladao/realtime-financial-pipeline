import os
import sys

import pytest

# Project root on path for `import src.*`
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "spark: tests that require a local PySpark session (not Kafka/Postgres)",
    )


@pytest.fixture(scope="module")
def spark_session():
    """Local Spark for transform / batch tests (no cluster, no Kafka)."""
    pytest.importorskip("pyspark")
    from pyspark.errors.exceptions.base import PySparkRuntimeError
    from pyspark.sql import SparkSession

    try:
        spark = (
            SparkSession.builder.master("local[1]")
            .appName("realtime-financial-pipeline-tests")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "2")
            .getOrCreate()
        )
    except PySparkRuntimeError as e:
        pytest.skip(
            "Local Spark JVM not available (install Java and set JAVA_HOME). "
            f"Original error: {e}"
        )
    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    spark.stop()
