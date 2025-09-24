import os

#postgresql+asyncpg://postgres:postgres@localhost:5432/file_service

BASE_DIR = os.getenv("BASE_DIR", "./uploads")
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/file_service")
