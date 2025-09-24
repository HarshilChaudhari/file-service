# Base class for storage adapters
from abc import ABC, abstractmethod

class BaseStorage(ABC):

    @abstractmethod
    async def save_file(self, user_code: str, file_kind: str, filename: str, content: bytes) -> str:
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> None:
        pass

    @abstractmethod
    async def get_file_path(self, file_path: str) -> str:
        pass
