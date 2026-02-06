FROM bitnami/spark:3.5.4

USER root

# Install dependencies
RUN install_packages python3-pip curl

# Copy and install Python dependencies
COPY requirements/spark-driver.txt /tmp/
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir -r /tmp/spark-driver.txt

# Config working directory
WORKDIR /app

# Copy source code
COPY src /app/src

# Create necessary directories with appropriate permissions
RUN mkdir -p /app/logs /app/checkpoints && \
    chown -R 1001:1001 /app

# Back to non-root user
USER 1001

CMD ["sleep", "infinity"]