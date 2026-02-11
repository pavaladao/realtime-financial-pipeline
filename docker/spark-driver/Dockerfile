FROM spark-base:3.5.3

USER root

COPY requirements/spark-driver.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt

USER spark

WORKDIR /app