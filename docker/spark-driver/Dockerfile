FROM spark-base:3.5.3

USER root

COPY requirements/spark-driver.txt /tmp/requirements.txt

# Instalar dependências Python
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt

# Verificar se foram instaladas corretamente
RUN echo "=== Verificando dependências Python ===" && \
    python3 -m pip list && \
    echo "" && \
    echo "=== Testando importações ===" && \
    python3 -c "import fastavro; print('✓ fastavro ok')" && \
    python3 -c "import requests; print('✓ requests ok')" && \
    python3 -c "import avro; print('✓ avro ok')" && \
    python3 -c "import dateutil; print('✓ python-dateutil ok')" && \
    echo "" && \
    echo "=== Python version ===" && \
    python3 --version

USER spark

WORKDIR /app

# Variáveis de ambiente para Python
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

# CMD ["spark-submit", \
#      "--master", "spark://spark-master:7077", \
#      "--deploy-mode", "client", \
#      "src/processors/streaming_processor.py"]