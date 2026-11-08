import logging
import os

from dotenv import load_dotenv

from src.app import create_app

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = create_app(os.environ)
