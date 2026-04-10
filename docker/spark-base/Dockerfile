FROM apache/spark:3.5.3

USER root

# ===== Install Python (stable & Spark-friendly) =====
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        ca-certificates \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ===== Install Python dependencies =====
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir \
        fastavro \
        requests \
        avro \
        python-dateutil

# ===== Normalize python path =====
RUN ln -sf /usr/bin/python3 /usr/bin/python

# ===== Spark env =====
ENV PYSPARK_PYTHON=/usr/bin/python3
ENV PYSPARK_DRIVER_PYTHON=/usr/bin/python3

# ===== PostgreSQL JDBC driver =====
RUN curl -o /opt/spark/jars/postgresql-42.7.3.jar \
    https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.3/postgresql-42.7.3.jar

# ===== S3A (MinIO / AWS) — match Spark 3.5.3’s Hadoop 3.3.4 (avoid hadoop-aws / common skew) =====
RUN curl -o /opt/spark/jars/hadoop-aws-3.3.4.jar \
    https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    curl -o /opt/spark/jars/aws-java-sdk-bundle-1.12.262.jar \
    https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar

# ===== Ivy cache (Kafka / Avro deps) =====
RUN mkdir -p /home/spark/.ivy2 && \
    chown -R spark:spark /home/spark/.ivy2

USER spark

WORKDIR /opt/spark