import os
from datetime import datetime
from app.config import BASE_DIR
from app.storage.base import BaseStorage

class LocalStorage(BaseStorage):

    async def save_file(self, user_code: str, file_kind: str, filename: str, content: bytes) -> str:
        # Month name instead of number
        now = datetime.now()
        month_name = now.strftime("%B")  # e.g., "September"
        dir_path = os.path.join(BASE_DIR, user_code, str(now.year), month_name, file_kind)
        os.makedirs(dir_path, exist_ok=True)

        file_path = os.path.join(dir_path, filename)
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    async def delete_file(self, file_path: str) -> None:
        if os.path.exists(file_path):
            os.remove(file_path)

    async def get_file_path(self, file_path: str) -> str:
        if os.path.exists(file_path):
            return file_path
        return None
