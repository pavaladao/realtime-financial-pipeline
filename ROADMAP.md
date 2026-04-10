# 🎯 ROADMAP COMPLETO: DATA ENGINEERING EM 6 SEMANAS

## 📊 VISÃO GERAL

**Objetivo:** Construir um Real-Time Financial Analytics Pipeline production-ready e conseguir vaga como Data Engineer

**Tempo Total:** 6 semanas (10-15h/semana = 60-90h total)

**Entregável Final:** Pipeline completo + portfólio GitHub + LinkedIn atualizado

---

## Estado atual do repositório (auditoria)

*Última revisão alinhada ao código em `src/`, `docker-compose.yaml`, `scripts/init-pipeline.ps1` e testes em `tests/`.*

### Implementado e funcional

- **Ingestão:** `src/producers/producer.py` — Finnhub WebSocket → Kafka (`confluent-kafka` + Avro + Schema Registry).
- **Topic Kafka:** `trades-data` (não `financial-trades`). Registro de schema: `src/producers/update_schema.py`, `src/schemas/finnhub_trades_schema.avsc`.
- **Infra Docker:** Kafka em modo **KRaft** (sem Zookeeper), Schema Registry, **MinIO** (lake S3-compatible), **PostgreSQL**, **Spark** (master, worker, driver custom). **Não** há Zookeeper, Kafka UI, Airflow, Grafana, Streamlit ou serviços do README na compose atual.
- **Portas úteis:** Kafka host `9092`, Schema Registry `8081`, Postgres host `5433`, MinIO API `9000` / console `9001`, **Spark Master UI `8080`** (não é Kafka UI).
- **Processamento:** `src/processors/streaming_processor.py` — Structured Streaming, `KafkaReader` + Avro (`kafka_reader.py`), agregações 1 min / 5 min + watermark (`trade_transforms.py`), escrita JDBC em Postgres (`postgres_batch.py`), anomalias volume > 3× média, lake Parquet opcional (`lake_batch.py`) com partição `year/month/day/hour`, Snappy, checkpoint em `/app/checkpoints/...` quando `LAKE_ENABLED`.
- **SQL:** `sql/init.sql` — tabelas alinhadas aos aggregates (incl. `anomalies`).
- **Dev:** `scripts/init-pipeline.ps1` — sobe stack, schema, topic, `spark-submit` no `spark-driver`.
- **Testes:** `pytest` em `tests/` (transforms, lake/postgres batch, kafka reader, wiring, layout, env, paths). **Sem** `tests/test_consumer.py`, **sem** CI GitHub Actions no repo, **sem** cobertura 80% formal ainda.

### README vs realidade

O **README** ainda descreve dbt, Airflow, Great Expectations, Grafana, GitHub Actions, etc.; isso é **roadmap / aspiracional**. Trate o pipeline **Python + Compose** acima como fonte de verdade até essas camadas existirem no repositório.

### Próximos passos sugeridos (ordem prática)

1. **Curto prazo:** DLQ + logging estruturado + troubleshooting no README; alinhar README “Quick Start” às portas reais; opcional **AWS S3** real espelhando o mesmo layout do MinIO.
2. **Semana 3+ do roadmap:** dbt em Postgres → depois Airflow → depois dashboard (Streamlit) e observabilidade (Prometheus/Grafana) se quiser fechar o plano original.
3. **Qualidade / entrega:** CI (lint + pytest), testes de integração com containers, `LICENSE` e documentação de arquitetura real (`ARCHITECTURE.md` ou diagrama).

---

# 🗓️ SEMANA 1: FUNDAMENTOS + SETUP

## DIA 1 (Segunda) - 2-3h: Planejamento & Setup Inicial

### O QUE ESTUDAR (2h)

- [x]  Docker básico (1h): containers, images, docker-compose
- [x]  Kafka conceitos (1h): topics, producers, consumers, partitions

**RECURSOS:**
- Docker: https://docs.docker.com/get-started/
- Kafka intro: https://kafka.apache.org/intro

### TASKS

- [x]  Instalar Docker Desktop
- [x]  Criar repositório GitHub: `realtime-financial-pipeline`
- [x]  Criar README.md básico com título e objetivo
- [x]  Criar estrutura de pastas: docker/, producers/, processors/, dags/, dashboard/, tests/, docs/

```text
realtime-financial-pipeline/
├── docker/
├── src/
│   ├── producers/
│   ├── processors/
│   └── consumers/
├── sql/
├── scripts/
├── tests/
└── (futuro: dags/, dashboard/, docs/)
```

### ENTREGÁVEL

✅ Repo no GitHub com estrutura criada

---

## DIA 2 (Terça) - 3h: Docker Environment

### O QUE ESTUDAR (3h)

- [x]  Docker Compose (1.5h): multi-container apps
- [x]  Kafka em Docker (1.5h): broker, listeners — *hoje: KRaft, sem Zookeeper*

**RECURSOS:**
- Docker Compose: https://docs.docker.com/compose/
- Confluent Kafka Docker: https://docs.confluent.io/platform/current/platform-quickstart.html

### TASKS

- [x]  Criar `docker-compose.yaml` com: Kafka (KRaft), Schema Registry, MinIO, Postgres, Spark — *sem Zookeeper; Kafka UI não está no compose*
- [x]  Subir ambiente: `docker compose up -d`
- [x]  Verificar serviços (Kafka `9092`, Schema Registry `8081`; Spark Master UI `http://localhost:8080` — não é Kafka UI)
- [x]  Topic do pipeline: `trades-data` *(criado via `init-pipeline.ps1` / `kafka-topics`)*

### ENTREGÁVEL

✅ Docker environment funcionando, topic criado

---

## DIA 3 (Quarta) - 3h: Python Producer Básico

### O QUE ESTUDAR (3h)

- [x]  Kafka Python client (1h): kafka-python library
- [x]  APIs financeiras (1h): Finnhub, Alpha Vantage
- [x]  WebSockets Python (1h)

**RECURSOS:**
- kafka-python: https://kafka-python.readthedocs.io/
- Finnhub API: https://finnhub.io/docs/api

### TASKS

- [x]  Criar conta Finnhub (grátis)
- [x]  Implementar `src/producers/producer.py` *(não `stock_producer.py`)*
- [x]  Implementar conexão WebSocket com Finnhub
- [x]  Produzir mensagens para Kafka topic
- [x]  Adicionar logging básico
- [x]  Testar com 3-5 símbolos (AAPL, GOOGL, MSFT, TSLA, AMZN)

### ENTREGÁVEL

✅ Producer enviando dados reais para Kafka

---

## DIA 4 (Quinta) - 2h: Kafka Consumer Teste

### O QUE ESTUDAR (2h)

- [x]  Kafka Consumers (1h): consumer groups, offsets
- [x]  JSON schema validation (1h)

### TASKS

- [ ]  Criar `tests/test_consumer.py` *(opcional — consumer de referência: `src/consumers/consumer.py`)*
- [x]  Consumir mensagens do topic `trades-data` *(ou validar via Spark/processor)*
- [x]  Printar dados no console
- [x]  Validar estrutura JSON
- [x]  Documentar schema esperado no README

### ENTREGÁVEL

✅ Consumer funcionando, dados sendo printados

---

## DIA 5 (Sexta) - 2h: Schema Registry

### O QUE ESTUDAR (2h)

- [x]  Avro schemas (1h)
- [x]  Confluent Schema Registry (1h)

### TASKS

- [x]  Schema Avro: `src/schemas/finnhub_trades_schema.avsc` (+ JSON espelho)
- [x]  Atualizar producer para usar Schema Registry
- [x]  Atualizar consumer para validar schema
- [x]  Testar backward compatibility

### ENTREGÁVEL

✅ Schema Registry configurado, validação funcionando

---

## DIA 6-7 (Fim de Semana) - 3h: Revisão & Documentação

### TASKS

- [x]  Limpar código da semana
- [x]  Adicionar docstrings
- [x]  README com visão geral *(alinhar screenshots à stack real: MinIO `9001`, Spark UI `8080`, etc.)*
- [x]  Commit e push tudo no GitHub
- [x]  Revisar conceitos aprendidos

### ENTREGÁVEL

✅ Semana 1 completa, código limpo no GitHub

---

# 🗓️ SEMANA 2: SPARK STREAMING

## DIA 8 (Segunda) - 3h: Spark Setup

### O QUE ESTUDAR (3h)

- [x]  Spark Structured Streaming (2h): concepts, micro-batches
- [x]  PySpark básico (1h)

**RECURSOS:**
- Spark Streaming: https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
- PySpark tutorial: https://spark.apache.org/docs/latest/api/python/

### TASKS

- [x]  Adicionar Spark ao docker-compose.yml: Spark Master, Spark Worker
- [x]  Criar processors/streaming_processor.py
- [x]  Conectar Spark com Kafka
- [x]  Ler stream do topic `trades-data`
- [x]  Printar no console (modo debug)

### ENTREGÁVEL

✅ Spark consumindo Kafka em real-time

---

## DIA 9 (Terça) - 3h: Transformações Básicas

### O QUE ESTUDAR (3h)

- [x]  PySpark transformations (1.5h): select, filter, withColumn
- [x]  Window functions (1.5h): time windows, aggregations

### TASKS

- [x]  Parse JSON do Kafka
- [x]  Adicionar timestamp de processamento
- [x]  Calcular agregações por janela de 1 minuto: Volume total, Preço médio, Preço min/max, Número de trades
- [x]  Printar resultados agregados

### ENTREGÁVEL

✅ Agregações funcionando em janelas de tempo

---

## DIA 10 (Quarta) - 3h: Métricas Avançadas

### O QUE ESTUDAR (3h)

- [x]  Métricas financeiras (1h): VWAP, volatilidade
- [x]  Stateful streaming (1h): watermarks, late data
- [x]  Window types (1h): tumbling, sliding, session

### TASKS

- [x]  Implementar VWAP (Volume Weighted Average Price)
- [x]  Calcular volatilidade (rolling standard deviation)
- [x]  Janela 5 min com slide 1 min (`aggregate_5min`); *15 min não implementado*
- [x]  Configurar watermarking para late data
- [x]  Adicionar detecção de anomalias simples (volume > 3x média)

### ENTREGÁVEL

✅ Métricas financeiras sendo calculadas

---

## DIA 11 (Quinta) - 3h: Storage - PostgreSQL

### O QUE ESTUDAR (3h)

- [x]  PostgreSQL com Spark (1h): JDBC connector
- [x]  Schema design (1h): normalized vs denormalized
- [x]  Indexing (1h)

### TASKS

- [x]  Adicionar PostgreSQL ao docker-compose.yml
- [x]  Criar database schema: trades_raw, trades_aggregated_1min, trades_aggregated_5min, anomalies
- [x]  Configurar Spark para escrever em PostgreSQL
- [x]  Criar índices apropriados
- [x]  Testar queries de performance

### ENTREGÁVEL

✅ Dados sendo escritos em PostgreSQL em real-time

---

## DIA 12 (Sexta) - 3h: Storage - S3 Data Lake

### O QUE ESTUDAR (3h)

- [x]  AWS S3 basics (1h): buckets, objects, permissions
- [x]  Parquet format (1h): columnar storage, compression
- [x]  Partitioning strategies (1h)

### TASKS

- [ ]  Criar conta AWS free tier *(opcional se usar só MinIO local)*
- [ ]  **Produção AWS:** criar bucket S3 `financial-pipeline-datalake` e credenciais; apontar `S3A_ENDPOINT` vazio / endpoint regional
- [x]  **Local:** MinIO no `docker-compose`, bucket via `minio-create-bucket`, credenciais em `.env`
- [x]  Spark S3A configurado (`lake_batch.py` + `apply_s3a_hadoop_conf`, variáveis `S3A_*` / `AWS_*`)
- [x]  Particionamento **year/month/day/hour** *(símbolo não particionado no path; coluna `symbol` nos dados)*
- [x]  Parquet + Snappy; checkpoint do stream lake em `/app/checkpoints/lake_raw` *(streaming_processor)*

### ENTREGÁVEL

✅ Data lake **bronze** em MinIO (dev) com Parquet; AWS S3 como passo opcional de produção

---

## DIA 13-14 (Fim de Semana) - 3h: Error Handling & Monitoring

### O QUE ESTUDAR (3h)

- [ ]  Spark exception handling (1h)
- [ ]  Dead letter queues (1h)
- [ ]  Logging estruturado (1h)

### TASKS

- [ ]  Implementar error handling robusto
- [ ]  Criar dead letter topic (ex.: `trades-data-dlq`) e roteamento de falhas
- [ ]  Adicionar logging estruturado (JSON logs)
- [ ]  Implementar retry logic com exponential backoff
- [ ]  Adicionar métricas de monitoring: Records processed/sec, Processing latency, Error rate
- [ ]  Documentar troubleshooting no README

### ENTREGÁVEL

✅ Pipeline robusto com error handling

---

# 🗓️ SEMANA 3: DBT + DATA QUALITY

## DIA 15 (Segunda) - 3h: dbt Setup

### O QUE ESTUDAR (3h)

- [ ]  dbt core concepts (1.5h): models, sources, tests
- [ ]  dbt-postgres (1.5h): setup, configuration

**RECURSOS:**
- dbt docs: https://docs.getdbt.com/docs/introduction
- dbt tutorial: https://docs.getdbt.com/tutorial/learning-more/getting-started

### TASKS

- [ ]  Instalar dbt: `pip install dbt-postgres`
- [ ]  Criar projeto dbt: `dbt init financial_pipeline`
- [ ]  Configurar conexão com PostgreSQL
- [ ]  Criar estrutura de pastas: models/staging/, models/intermediate/, models/marts/
- [ ]  Criar primeiro model: staging/stg_trades.sql
- [ ]  Rodar: `dbt run`

### ENTREGÁVEL

✅ dbt configurado, primeiro model rodando

---

## DIA 16 (Terça) - 3h: Data Modeling - Staging

### O QUE ESTUDAR (3h)

- [ ]  Staging layer (1h): raw to cleaned
- [ ]  SQL best practices (1h)
- [ ]  dbt macros (1h)

### TASKS

- [ ]  Criar models staging: stg_trades.sql, stg_aggregated_1min.sql, stg_aggregated_5min.sql
- [ ]  Adicionar data cleaning: Remove nulls, Cast tipos corretos, Standardize símbolos (uppercase), Adicionar surrogate keys
- [ ]  Documentar columns no schema.yml

### ENTREGÁVEL

✅ Staging models criados e testados

---

## DIA 17 (Quarta) - 3h: Data Modeling - Marts

### O QUE ESTUDAR (3h)

- [ ]  Kimball dimensional modeling (1.5h): facts, dimensions
- [ ]  Slowly changing dimensions (1.5h)

### TASKS

- [ ]  Criar dimension tables: dim_symbols.sql, dim_date.sql
- [ ]  Criar fact tables: fct_trades.sql, fct_daily_summary.sql
- [ ]  Implementar SCD Type 2 para dim_symbols

### ENTREGÁVEL

✅ Data warehouse dimensional criado

---

## DIA 18 (Quinta) - 3h: dbt Tests & Documentation

### O QUE ESTUDAR (3h)

- [ ]  dbt tests (1.5h): singular, generic tests
- [ ]  dbt docs (1.5h): generate, serve

### TASKS

- [ ]  Adicionar tests genéricos: unique, not_null, accepted_values, relationships (foreign keys)
- [ ]  Criar custom tests: price_within_range, volume_positive, no_future_dates
- [ ]  Documentar todos os models no schema.yml
- [ ]  Gerar documentação: `dbt docs generate`
- [ ]  Servir docs: `dbt docs serve`
- [ ]  Screenshot e adicionar no README

### ENTREGÁVEL

✅ 100% dos models com tests e documentação

---

## DIA 19 (Sexta) - 3h: Great Expectations

### O QUE ESTUDAR (3h)

- [ ]  Great Expectations (2h): setup, expectations
- [ ]  Data quality frameworks (1h)

**RECURSOS:**
- Great Expectations: https://docs.greatexpectations.io/

### TASKS

- [ ]  Instalar Great Expectations
- [ ]  Inicializar: `great_expectations init`
- [ ]  Criar expectation suites: trades_raw_suite, trades_aggregated_suite
- [ ]  Adicionar expectations: Column values to be between, Column values to not be null, Table row count to be between, Column mean to be between
- [ ]  Configurar validations automáticas
- [ ]  Gerar Data Docs

### ENTREGÁVEL

✅ Data quality checks rodando automaticamente

---

## DIA 20-21 (Fim de Semana) - 3h: Refactoring & Optimization

### TASKS

- [ ]  Refatorar código dbt (DRY principles)
- [ ]  Criar macros reutilizáveis
- [ ]  Otimizar queries SQL (EXPLAIN ANALYZE)
- [ ]  Adicionar incremental models (performance)
- [ ]  Documentar data lineage
- [ ]  Atualizar README com: Diagramas de data flow, Como rodar dbt, Como visualizar docs

### ENTREGÁVEL

✅ Código otimizado, documentação completa

---

# 🗓️ SEMANA 4: AIRFLOW + ORCHESTRATION

## DIA 22 (Segunda) - 3h: Airflow Setup

### O QUE ESTUDAR (3h)

- [ ]  Airflow concepts (1.5h): DAGs, operators, sensors
- [ ]  Airflow architecture (1.5h): scheduler, executor, webserver

**RECURSOS:**
- Airflow docs: https://airflow.apache.org/docs/

### TASKS

- [ ]  Adicionar Airflow ao docker-compose.yml: Postgres (metadata DB), Redis (celery backend), Webserver, Scheduler, Worker
- [ ]  Subir Airflow: `docker-compose up airflow-init`
- [ ]  Acessar UI Airflow em porta **diferente de 8080** *(8080 = Spark Master neste projeto)* ou desligar Spark ao desenvolver Airflow local
- [ ]  Criar primeiro DAG: hello_world.py
- [ ]  Verificar que aparece na UI

### ENTREGÁVEL

✅ Airflow rodando, UI acessível

---

## DIA 23 (Terça) - 3h: DAG 1 - Pipeline Health Monitor

### O QUE ESTUDAR (3h)

- [ ]  Sensors (1h): external task, file, custom
- [ ]  Branching (1h): conditional execution
- [ ]  Alerting (1h): email, Slack

### TASKS

- [ ]  Criar DAG: monitor_pipeline_health.py
- [ ]  Adicionar tasks: Check Kafka lag, Check Spark job status, Check PostgreSQL row count, Check S3 file freshness, Alert if thresholds exceeded
- [ ]  Configurar schedule: `/10 * * * *` (a cada 10min)
- [ ]  Configurar email alerts

### ENTREGÁVEL

✅ DAG de monitoring funcionando

---

## DIA 24 (Quarta) - 3h: DAG 2 - dbt Orchestration

### O QUE ESTUDAR (3h)

- [ ]  BashOperator (1h)
- [ ]  Task dependencies (1h)
- [ ]  Backfills (1h)

### TASKS

- [ ]  Criar DAG: run_dbt_transformations.py
- [ ]  Adicionar tasks: dbt deps, dbt seed, dbt run (staging → intermediate → marts), dbt test, dbt docs generate
- [ ]  Configurar schedule: `0 * * * *` (hourly)
- [ ]  Adicionar retry logic
- [ ]  Implementar data quality gates (fail se tests falham)

### ENTREGÁVEL

✅ dbt rodando via Airflow

---

## DIA 25 (Quinta) - 3h: DAG 3 - Data Quality Checks

### O QUE ESTUDAR (3h)

- [ ]  Custom operators (1h)
- [ ]  XComs (1h): pass data between tasks
- [ ]  Task groups (1h)

### TASKS

- [ ]  Criar DAG: data_quality_checks.py
- [ ]  Integrar Great Expectations
- [ ]  Adicionar tasks: Run expectation suites, Generate data quality report, Store results em PostgreSQL, Alert on failures
- [ ]  Usar task groups para organizar
- [ ]  Schedule: `0 */6 * * *` (a cada 6h)

### ENTREGÁVEL

✅ Data quality automático

---

## DIA 26 (Sexta) - 3h: DAG 4 - Alerting & Reporting

### O QUE ESTUDAR (3h)

- [ ]  Callbacks (1h): on_success, on_failure
- [ ]  Slack integration (1h)
- [ ]  Custom alerts (1h)

### TASKS

- [ ]  Criar DAG: daily_report.py
- [ ]  Gerar relatório diário: Total trades processados, Anomalias detectadas, Pipeline uptime, Data quality score, Performance metrics
- [ ]  Enviar via Slack/Email
- [ ]  Schedule: `0 9 * * *` (9am daily)
- [ ]  Adicionar callbacks em todos os DAGs

### ENTREGÁVEL

✅ Sistema de alerting completo

---

## DIA 27-28 (Fim de Semana) - 4h: Monitoring Dashboard

### O QUE ESTUDAR (4h)

- [ ]  Prometheus + Grafana (2h)
- [ ]  Airflow metrics (1h)
- [ ]  Custom metrics (1h)

### TASKS

- [ ]  Adicionar Prometheus + Grafana ao Docker
- [ ]  Configurar Airflow metrics export
- [ ]  Criar dashboards Grafana: DAG success rate, Task duration, Pipeline throughput, Error rate, Data freshness
- [ ]  Screenshot e adicionar no README

### ENTREGÁVEL

✅ Monitoring dashboard visual

---

# 🗓️ SEMANA 5: DASHBOARD + VISUALIZAÇÃO

## DIA 29 (Segunda) - 3h: Streamlit Setup

### O QUE ESTUDAR (3h)

- [ ]  Streamlit basics (2h): components, layout
- [ ]  Real-time updates (1h): st.experimental_rerun

**RECURSOS:**
- Streamlit docs: https://docs.streamlit.io/

### TASKS

- [ ]  Criar dashboard/app.py
- [ ]  Setup básico: título, sidebar, layout
- [ ]  Conectar com PostgreSQL
- [ ]  Criar primeira visualização: tabela de trades recentes
- [ ]  Adicionar auto-refresh (a cada 5 segundos)
- [ ]  Testar localmente: `streamlit run app.py`

### ENTREGÁVEL

✅ Dashboard básico funcionando

---

## DIA 30 (Terça) - 3h: Real-Time Charts

### O QUE ESTUDAR (3h)

- [ ]  Plotly (1.5h): line charts, candlestick
- [ ]  Streamlit charts (1.5h)

### TASKS

- [ ]  Adicionar gráficos: Preço em tempo real (line chart), Volume por minuto (bar chart), VWAP vs preço (dual axis), Top 10 símbolos por volume
- [ ]  Adicionar filtros: Seletor de símbolo, Range de datas, Janela de agregação (1min, 5min, 15min)
- [ ]  Implementar caching para performance

### ENTREGÁVEL

✅ Charts em tempo real

---

## DIA 31 (Quarta) - 3h: Anomaly Detection View

### O QUE ESTUDAR (3h)

- [ ]  Streamlit alerts (1h)
- [ ]  Color coding (1h)
- [ ]  Interactive tables (1h)

### TASKS

- [ ]  Criar página “Anomalias”
- [ ]  Exibir anomalias recentes (últimas 24h)
- [ ]  Adicionar alertas visuais: st.error(), st.warning(), Color coding
- [ ]  Adicionar tabela interativa com: Timestamp, Símbolo, Tipo de anomalia, Severidade, Contexto
- [ ]  Gráfico: anomalias ao longo do tempo

### ENTREGÁVEL

✅ Página de anomalias funcionando

---

## DIA 32 (Quinta) - 3h: Metrics & KPIs

### O QUE ESTUDAR (3h)

- [ ]  Streamlit metrics (1h)
- [ ]  Dashboard layout (2h): columns, containers

### TASKS

- [ ]  Criar página “Overview”
- [ ]  Adicionar KPIs principais: Total trades (today), Volume total ($), Pipeline uptime (%), Average latency (ms), Data quality score (%)
- [ ]  Usar st.metric() com delta
- [ ]  Adicionar sparklines (mini gráficos)
- [ ]  Layout em grid (3 colunas)

### ENTREGÁVEL

✅ Dashboard de KPIs

---

## DIA 33 (Sexta) - 3h: Pipeline Health Page

### O QUE ESTUDAR (3h)

- [ ]  Status indicators (1h)
- [ ]  Logs visualization (2h)

### TASKS

- [ ]  Criar página “Pipeline Health”
- [ ]  Exibir status de cada componente: Kafka, Spark Streaming, PostgreSQL, S3, Airflow DAGs
- [ ]  Mostrar métricas de cada componente
- [ ]  Exibir logs recentes (últimos 100)
- [ ]  Botão para download de logs

### ENTREGÁVEL

✅ Página de health check completa

---

## DIA 34-35 (Fim de Semana) - 4h: Polish & Performance

### TASKS

- [ ]  Otimizar queries do dashboard (indexing)
- [ ]  Adicionar loading spinners
- [ ]  Implementar caching estratégico
- [ ]  Melhorar UX: Tooltips explicativos, Help section, Responsive design
- [ ]  Adicionar tema customizado (cores da marca)
- [ ]  Testar performance com dados reais
- [ ]  Screenshot de todas as páginas para README

### ENTREGÁVEL

✅ Dashboard production-ready

---

# 🗓️ SEMANA 6: TESTES + DOCUMENTAÇÃO + DEPLOY

## DIA 36 (Segunda) - 3h: Unit Tests

### O QUE ESTUDAR (3h)

- [x]  pytest (1.5h): fixtures, parametrize — *`tests/conftest.py`, `spark_session`*
- [ ]  Mocking (1.5h): unittest.mock — *expandir para producer/integrações*

**RECURSOS:**
- pytest docs: https://docs.pytest.org/

### TASKS

- [x]  Suite em `tests/` *(layout, env, paths, transforms, lake/postgres batch, kafka reader, wiring)*
- [ ]  Ampliar cobertura: producer, consumer, integração Kafka
- [ ]  Alcançar >80% code coverage
- [ ]  Configurar `pytest.ini` / `pyproject.toml` opcional
- [ ]  Rodar: `pytest --cov`

### ENTREGÁVEL

✅ Testes principais passando; **meta de cobertura e CI ainda em aberto**

---

## DIA 37 (Terça) - 3h: Integration Tests

### O QUE ESTUDAR (3h)

- [ ]  Docker test containers (1.5h)
- [ ]  End-to-end testing (1.5h)

### TASKS

- [ ]  Criar `tests/integration/` *(ou job Compose + health checks)*
- [ ]  Cenários: Kafka → Spark, Spark → Postgres, Spark → MinIO/S3; *dbt quando existir*
- [ ]  Testcontainers ou script E2E com `docker compose`
- [ ]  Workflow CI (GitHub Actions / outro) rodando `pytest`
- [ ]  Documentar como rodar testes de integração

### ENTREGÁVEL

✅ Integration tests funcionando *(não iniciado no repo)*

---

## DIA 38 (Quarta) - 3h: Load Testing

### O QUE ESTUDAR (3h)

- [ ]  Load testing concepts (1h)
- [ ]  Locust (2h): scenarios, users

### TASKS

- [ ]  Instalar Locust
- [ ]  Criar tests/load/locustfile.py
- [ ]  Simular carga: 100 events/sec, 1,000 events/sec, 10,000 events/sec
- [ ]  Medir: Latência end-to-end, Throughput, CPU/Memory usage, Error rate
- [ ]  Documentar resultados no README
- [ ]  Identificar gargalos

### ENTREGÁVEL

✅ Relatório de performance

---

## DIA 39 (Quinta) - 4h: Documentação Completa

### O QUE ESTUDAR (4h)

- [ ]  Technical writing (2h)
- [ ]  Diagramming (2h): draw.io, Mermaid

### TASKS

- [ ]  Criar diagramas profissionais: Arquitetura geral, Data flow detalhado, Deployment architecture
- [ ]  Escrever README completo: Intro, Architecture, Prerequisites, Quick Start, Detailed Setup, Usage, Monitoring, Performance, Troubleshooting, Future Improvements
- [ ]  Criar ARCHITECTURE.md detalhado
- [ ]  Criar CONTRIBUTING.md
- [ ]  Adicionar badges ao README: Build status, Code coverage, License, Python version

### ENTREGÁVEL

✅ Documentação profissional completa

---

## DIA 40 (Sexta) - 4h: CI/CD Setup

### O QUE ESTUDAR (4h)

- [ ]  GitHub Actions (2h): workflows, jobs
- [ ]  Docker Hub (1h)
- [ ]  Deployment strategies (1h)

### TASKS

- [ ]  Criar .github/workflows/ci.yml: Run tests on PR, Check code coverage, Lint code, Build Docker images
- [ ]  Criar .github/workflows/deploy.yml: Deploy on merge to main, Push Docker images to Docker Hub, Update documentation
- [ ]  Configurar secrets no GitHub
- [ ]  Testar workflow completo

### ENTREGÁVEL

✅ CI/CD pipeline funcionando

---

## DIA 41-42 (Fim de Semana) - 6h: DEPLOY + POLISH FINAL

### SÁBADO (3h)

- [ ]  Deploy completo em cloud (AWS/GCP)
- [ ]  Configurar domínio customizado (opcional)
- [ ]  Testar tudo em produção
- [ ]  Monitoring em produção funcionando
- [ ]  Configurar backups automáticos
- [ ]  Documentar processo de deploy

### DOMINGO (3h)

- [ ]  Code review completo (self-review)
- [ ]  Refatorar código problemático
- [ ]  Adicionar comentários onde necessário
- [ ]  Verificar todos os TODOs removidos
- [ ]  Gravar demo video (2-3min)
- [ ]  Fazer screenshots bonitos
- [ ]  Último commit: “Release v1.0”
- [ ]  Criar release no GitHub

### ENTREGÁVEL

✅ Projeto 100% completo e deployado

---

# 📊 CHECKLIST FINAL DE QUALIDADE

## Código

- [ ]  Todos os tests passando (unit + integration) — *unitários principais ok; integração pendente*
- [ ]  Code coverage > 80%
- [ ]  Sem warnings no linter
- [ ]  Código comentado adequadamente
- [ ]  Variáveis com nomes claros
- [ ]  Funções pequenas e focadas
- [ ]  Sem código duplicado

## Documentação

- [ ]  README alinhado à stack real *(portas, serviços, sem Airflow/Grafana até existirem)*
- [ ]  Diagramas de arquitetura claros
- [ ]  Quick start funciona em 5min *(validar no Windows + `init-pipeline.ps1`)*
- [ ]  Troubleshooting guide útil
- [ ]  Todos os comandos documentados
- [ ]  Screenshots atualizados
- [ ]  Demo video gravado

## Funcionalidade

- [x]  Pipeline processa dados em streaming *(Structured Streaming + Postgres + lake opcional)*
- [ ]  Latência < 500ms end-to-end *(medir e documentar)*
- [ ]  Data quality checks funcionando *(dbt/GE não no repo)*
- [ ]  Alerting funcionando
- [ ]  Dashboard atualizando automaticamente
- [ ]  Pode processar 10k events/sec *(load test)*
- [ ]  Fault-tolerant (recupera de falhas) — *checkpoints lake; DLQ/retry em aberto*

## DevOps

- [x]  Docker compose sobe stack principal *(rebuild após mudanças em imagens Spark)*
- [ ]  CI/CD pipeline verde
- [ ]  Deployado em cloud
- [ ]  Monitoring funcionando
- [ ]  Logs estruturados e úteis
- [ ]  Backups configurados

## Profissionalismo

- [ ]  GitHub repo organizado
- [ ]  Commits com mensagens claras
- [ ]  Branches organizadas (main, develop)
- [ ]  Issues/PRs se relevante
- [ ]  License file
- [ ]  Code of conduct

---

# 🎯 DELIVERABLES FINAIS

## 1. GitHub Repository

- [ ]  Código production-ready — *core streaming ok; hardening em aberto*
- [ ]  100% documentado
- [x]  Tests principais passando (`pytest`)
- [ ]  CI/CD configurado

## 2. Live Demo

- [ ]  Pipeline rodando em cloud
- [ ]  Dashboard acessível publicamente
- [ ]  Dados reais sendo processados

## 3. Portfólio Piece

- [ ]  Demo video (2-3min)
- [ ]  Blog post explicando o projeto
- [ ]  LinkedIn post anunciando

## 4. Skills Comprovadas

- [x]  Kafka + Spark Streaming *(núcleo do projeto)*
- [ ]  dbt + Data Modeling
- [ ]  Airflow + Orchestration
- [ ]  AWS + Cloud Infrastructure — *MinIO local feito; S3 real opcional*
- [x]  Docker + DevOps *(parcial — sem CI)*
- [ ]  Testing + CI/CD — *pytest presente; CI e integração pendentes*
- [ ]  Data Quality + Monitoring

---

# 📈 APÓS O PROJETO

## SEMANA 7: LinkedIn & Networking

- [ ]  Atualizar LinkedIn: Headline, Adicionar projeto, Mencionar skills
- [ ]  Post anunciando o projeto: Demo GIF/video, Explicar stack, Link GitHub, Hashtags
- [ ]  Escrever blog post no Medium/Dev.to
- [ ]  Participar de comunidades: Data Engineering Subreddit, Apache Kafka Slack, dbt Slack, Local meetups

## SEMANA 8: Applications & Interviews

- [ ]  Preparar STAR stories sobre o projeto
- [ ]  Praticar explicar arquitetura (whiteboard)
- [ ]  Revisar conceitos técnicos: Kafka internals, Spark optimizations, SQL query optimization, System design
- [ ]  Aplicar para 10-15 vagas/semana
- [ ]  Customizar resume por vaga
- [ ]  Preparar para behavioral interviews
- [ ]  Fazer mock interviews

---

# 💡 DICAS DE PRODUTIVIDADE

## Daily Routine

- [ ]  Manhã (1-2h): Teoria + estudar conceitos novos
- [ ]  Tarde/Noite (1-2h): Hands-on + coding
- [ ]  Fim do dia (15min): Commit, documentar, planejar amanhã

## Quando Travar

1. Ler documentação oficial (não Stack Overflow primeiro)
2. Debugar sistematicamente (logs, breakpoints)
3. Buscar em fóruns específicos (Kafka users, Spark users)
4. Perguntar em Slack communities
5. Fazer uma pausa (volta com mente fresca)

## Avoid Burn