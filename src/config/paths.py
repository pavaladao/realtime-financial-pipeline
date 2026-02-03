import os

# Project source directory
PROJECT_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Scheama paths
SCHEMAS_DIR = os.path.join(PROJECT_SRC, "schemas")
FINNHUB_TRADES_AVRO_SCHEMA = os.path.join(SCHEMAS_DIR, "finnhub_trades_schema.avsc")
FINNHUB_TRADES_JSON_SCHEMA = os.path.join(SCHEMAS_DIR, "finnhub_trades_schema.json")