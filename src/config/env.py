import os
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(os.path.join(ROOT_DIR, ".env"))

FINNHUB_TOKEN = os.getenv("FINNHUB_TOKEN")
