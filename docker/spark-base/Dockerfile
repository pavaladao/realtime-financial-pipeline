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

# ===== Ivy cache (Kafka / Avro deps) =====
RUN mkdir -p /home/spark/.ivy2 && \
    chown -R spark:spark /home/spark/.ivy2

USER spark

WORKDIR /opt/spark