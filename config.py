from dotenv import load_dotenv
import os

load_dotenv()

AZURE_LANGUAGE_KEY      = os.getenv("AZURE_LANGUAGE_KEY")
AZURE_LANGUAGE_ENDPOINT = os.getenv("AZURE_LANGUAGE_ENDPOINT")

DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = int(os.getenv("DB_PORT", 5432))
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME     = os.getenv("DB_NAME", "smart_helpdesk")
DB_SSLMODE  = os.getenv("DB_SSLMODE", "require")