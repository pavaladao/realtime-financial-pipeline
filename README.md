# Real-Time Financial Analytics Pipeline

End-to-end streaming pipeline: Finnhub WebSocket → Kafka (Avro) → Spark Structured Streaming → PostgreSQL, with an optional **MinIO** (S3-compatible) Parquet lake for local development.

![Project Status](https://img.shields.io/badge/status-in%20development-yellow)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)

## Project overview

The goal is a portfolio-grade data engineering stack: real-time ingestion, stream processing, relational analytics storage, and (optionally) object storage for the bronze layer. Throughput and latency depend on your hardware and Finnhub rate limits—treat performance numbers in older docs as targets until you measure them.

### Implemented today

- **Ingestion:** Python producer (`src/producers/producer.py`) — Finnhub WebSocket → Kafka topic **`trades-data`** via Confluent Avro + **Schema Registry**
- **Processing:** PySpark **Structured Streaming** — Avro decode (`kafka_reader.py`), 1-minute and 5-minute aggregates, VWAP, volatility, **anomaly detection** (volume > 3× batch average) (`trade_transforms.py`, `postgres_batch.py`)
- **Storage:** **PostgreSQL** for aggregates and anomalies (`sql/init.sql`); optional **Parquet** on **MinIO** when `LAKE_ENABLED=true` (`lake_batch.py`, partitioned by `year/month/day/hour`, Snappy)
- **Infra:** Docker Compose — Kafka (KRaft), Schema Registry, MinIO, PostgreSQL, Spark (master, worker, **spark-driver**)
- **Dev workflow:** [`scripts/init-pipeline.ps1`](scripts/init-pipeline.ps1) — compose, schema registration, topic creation, `spark-submit` inside `spark-driver`
- **Tests:** `pytest` under [`tests/`](tests/)

### Planned (see [ROADMAP.md](ROADMAP.md))

dbt on Postgres, Airflow, Streamlit dashboard, Great Expectations, Grafana/Prometheus, GitHub Actions CI, AWS S3 in production, etc.

## Architecture (current)

```
Finnhub WebSocket
       │
       ▼
┌──────────────┐     ┌──────────────────┐
│   Producer   │────►│  Kafka + Schema  │
│   (Python)   │     │    Registry      │
└──────────────┘     └────────┬─────────┘
                              │
                              ▼
                     ┌────────────────┐
                     │ Spark Streaming │
                     │ (driver cluster)│
                     └────────┬────────┘
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌────────────┐  ┌────────────┐  ┌────────────┐
       │  MinIO     │  │ PostgreSQL │  │ (future:   │
       │  Parquet   │  │  tables    │  │  dbt, UI)  │
       │  (optional)│  │            │  │            │
       └────────────┘  └────────────┘  └────────────┘
```

## Tech stack

| Layer | In use |
|--------|--------|
| Ingestion | Finnhub WebSocket, `confluent-kafka`, Avro |
| Messaging | Apache Kafka (KRaft), Confluent Schema Registry |
| Processing | Apache Spark 3.5.x, PySpark Structured Streaming |
| Analytics DB | PostgreSQL 16 |
| Object store (dev) | MinIO (S3 API); production can use AWS S3 with the same S3A settings |
| Containers | Docker Compose |
| Tests | pytest |

## Quick start

### Prerequisites

- **Docker Desktop** (Compose v2)
- **Python 3.9+** (for the producer and schema scripts on the host)
- **Finnhub API key** — [finnhub.io](https://finnhub.io/)

AWS is **not** required for local runs; MinIO acts as the lake. Use real S3 when you deploy to AWS and clear or repoint `S3A_ENDPOINT` per [`.env.example`](.env.example).

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/realtime-financial-pipeline.git
cd realtime-financial-pipeline
cp .env.example .env
```

Edit `.env` and set **`FINNHUB_TOKEN`**. For local MinIO, the defaults in `.env.example` usually match Compose (`MINIO_ROOT_*` aligned with `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`).

### 2. Start infrastructure

```bash
docker compose up -d
```

### 3. Run the streaming job (recommended on Windows)

From the repo root:

```powershell
.\scripts\init-pipeline.ps1
```

This waits for ports, registers the Avro schema, ensures topic **`trades-data`**, and runs `spark-submit` in the **`spark-driver`** container. The script blocks in the foreground—use another terminal for the producer (step 4).

On other platforms, replicate the steps in `init-pipeline.ps1` (compose, `python -m src.producers.update_schema`, `docker exec … spark-submit` with the same `--packages` as the script).

### 4. Start the producer (second terminal)

Repo root must be on `PYTHONPATH` so `import src` works.

**Linux / macOS:**

```bash
export PYTHONPATH="$(pwd)"
python -m src.producers.producer
```

**Windows PowerShell:**

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m src.producers.producer
```

### Services and ports (host)

| Service | URL / port |
|---------|------------|
| Kafka | `localhost:9092` |
| Schema Registry | `http://localhost:8081` |
| PostgreSQL | `localhost:5433` → container `5432` |
| MinIO S3 API | `http://localhost:9000` |
| MinIO console | `http://localhost:9001` |
| Spark Master UI | `http://localhost:8080` |

There is **no** Kafka UI or Airflow in this Compose file. Spark driver UI is often at `http://localhost:4040` while a job runs.

## Data flow

1. **Ingestion:** Trades from Finnhub are serialized with the registered Avro schema and sent to **`trades-data`**.
2. **Streaming:** Spark reads Kafka, deserializes Avro, builds 1-minute tumbling and 5-minute sliding windows (with watermarks).
3. **Metrics:** VWAP, volatility, min/max/avg price, trade counts; anomalies when volume exceeds **3×** the average in the batch path (`postgres_batch.py`).
4. **Storage:** Aggregates and anomalies go to **PostgreSQL**. If **`LAKE_ENABLED`** is true, raw exploded trades are written as **Snappy Parquet** under `s3a://<bucket>/trades_raw` with Hive-style partitions (`year/month/day/hour`).

## Example SQL (PostgreSQL)

Tables are defined in [`sql/init.sql`](sql/init.sql) (e.g. `trades_aggregated_1min`, `trades_aggregated_5min`, `anomalies`). Example:

```sql
-- Recent 1-minute bars
SELECT window_start, symbol, avg_price, vwap, trade_count
FROM trades_aggregated_1min
ORDER BY window_start DESC
LIMIT 20;

-- Recent anomalies
SELECT *
FROM anomalies
ORDER BY detected_at DESC
LIMIT 50;
```

## Project structure

```
realtime-financial-pipeline/
├── docker-compose.yaml
├── docker/
│   ├── spark-base/Dockerfile
│   └── spark-driver/Dockerfile
├── sql/
│   └── init.sql
├── scripts/
│   └── init-pipeline.ps1
├── src/
│   ├── config/
│   ├── consumers/
│   ├── producers/
│   ├── processors/       # Spark streaming, Kafka Avro, lake, Postgres batches
│   └── schemas/          # finnhub_trades_schema.avsc (+ JSON)
├── requirements/
│   ├── producer.txt
│   └── spark-driver.txt
├── tests/
├── .env.example
├── README.md
└── ROADMAP.md
```

## Testing

```bash
pytest
```

Some tests need **Java** / **PySpark** (`tests/conftest.py`). On Windows, ensure `JAVA_HOME` is set if Spark tests skip or fail.

## Configuration (summary)

See [`.env.example`](.env.example) for the full list. Important variables:

| Variable | Purpose |
|----------|---------|
| `FINNHUB_TOKEN` | Finnhub API key (producer) |
| `POSTGRES_*` | DB name, user, password (Compose defaults match `sql/init.sql` usage) |
| `LAKE_ENABLED` | `true`/`false` — write Parquet to MinIO/S3 |
| `S3A_ENDPOINT` | e.g. `http://minio:9000` in Docker; empty for default AWS endpoints |
| `S3A_BUCKET` | Lake bucket name |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | MinIO credentials locally; real AWS keys in cloud |

Spark in Docker uses **`kafka:29092`** and **`http://schema-registry:8081`**. The host producer uses **`localhost:9092`** and **`localhost:8081`**.

## Troubleshooting

**Kafka**

```bash
docker compose logs kafka
```

There is **no** Zookeeper service—Kafka runs in **KRaft** mode.

**Spark**

- Master UI: `http://localhost:8080`
- Driver UI (while job runs): often `http://localhost:4040`
- Rebuild images after changing Spark/JAR dependencies: `docker compose build spark-base spark-driver`

**Producer cannot connect**

- Ensure Schema Registry has the subject (`update_schema` / `init-pipeline.ps1`).
- Topic name must be **`trades-data`** (matches producer and streaming job).

**Out of memory**

Increase CPUs / memory in Docker Desktop **Settings → Resources**.

## Roadmap

Detailed week-by-week plan and status: **[ROADMAP.md](ROADMAP.md)**.

## Contributing

Fork, branch, and open a PR. Add tests for new behavior under `tests/` and update [`tests/test_project_layout.py`](tests/test_project_layout.py) if you add core pipeline files.

## License

Specify a license by adding a `LICENSE` file to the repository (e.g. MIT). Until then, all rights reserved unless you state otherwise.

## Acknowledgments

- [Finnhub](https://finnhub.io/) for market data APIs  
- [Apache Spark](https://spark.apache.org/) and [Apache Kafka](https://kafka.apache.org/) communities  
- [Confluent](https://www.confluent.io/) for Schema Registry documentation  

---

If this project is useful, consider starring the repo.
