import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USER")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")