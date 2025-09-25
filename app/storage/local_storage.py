import os
from datetime import datetime
from app.config import BASE_DIR
from app.storage.base import BaseStorage

class LocalStorage(BaseStorage):

    async def save_file(self, user_code: str, filename: str, content: bytes) -> str:
        now = datetime.now()
        month_name = now.strftime("%B")
        relative_path = os.path.join(user_code, str(now.year), month_name, filename)

        abs_path = os.path.join(BASE_DIR, relative_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "wb") as f:
            f.write(content)

        return relative_path  # return only relative path

    async def delete_file(self, relative_path: str) -> None:
        abs_path = os.path.join(BASE_DIR, relative_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)

    async def get_file_path(self, relative_path: str) -> str:
        abs_path = os.path.join(BASE_DIR, relative_path)
        if os.path.exists(abs_path):
            return abs_path
        return None
