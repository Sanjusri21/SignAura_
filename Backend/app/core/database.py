import logging
import asyncio
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("signaura.database")

class MockCollection:
    """In-memory collection fallback when MongoDB server is offline."""
    def __init__(self, name: str):
        self.name = name
        self._data: Dict[str, Dict[str, Any]] = {}

    async def insert_one(self, doc: Dict[str, Any]):
        doc_id = doc.get("id") or doc.get("_id") or str(len(self._data) + 1)
        doc["_id"] = doc_id
        if "id" not in doc:
            doc["id"] = doc_id
        self._data[str(doc_id)] = dict(doc)
        class InsertResult:
            inserted_id = doc_id
        return InsertResult()

    async def find_one(self, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for item in self._data.values():
            match = True
            for k, v in filter_dict.items():
                if k == "_id" and str(item.get("_id")) == str(v):
                    continue
                if item.get(k) != v:
                    match = False
                    break
            if match:
                return dict(item)
        return None

    def find(self, filter_dict: Optional[Dict[str, Any]] = None, sort: Optional[List] = None, limit: Optional[int] = None):
        filter_dict = filter_dict or {}
        class AsyncCursor:
            def __init__(self, items: List[Dict[str, Any]]):
                self.items = items
            def sort(self, *args, **kwargs):
                return self
            def limit(self, l: int):
                self.items = self.items[:l]
                return self
            async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
                if length is not None:
                    return self.items[:length]
                return self.items
            def __aiter__(self):
                self._iter = iter(self.items)
                return self
            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        matching = []
        for item in self._data.values():
            match = True
            for k, v in filter_dict.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                matching.append(dict(item))
        return AsyncCursor(matching)

    async def update_one(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        doc = await self.find_one(filter_dict)
        if doc:
            doc_id = str(doc.get("_id") or doc.get("id"))
            if "$set" in update_dict:
                self._data[doc_id].update(update_dict["$set"])
            else:
                self._data[doc_id].update(update_dict)
        class UpdateResult:
            modified_count = 1 if doc else 0
        return UpdateResult()

    async def delete_one(self, filter_dict: Dict[str, Any]):
        doc = await self.find_one(filter_dict)
        if doc:
            doc_id = str(doc.get("_id") or doc.get("id"))
            if doc_id in self._data:
                del self._data[doc_id]
        class DeleteResult:
            deleted_count = 1 if doc else 0
        return DeleteResult()

class MockDatabase:
    """Mock MongoDB Database."""
    def __init__(self):
        self._collections: Dict[str, MockCollection] = {}

    def __getitem__(self, name: str) -> MockCollection:
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]

    def get_collection(self, name: str) -> MockCollection:
        return self[name]

class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[Any] = None
    is_connected: bool = False

    async def connect_to_database(self):
        try:
            logger.info("Attempting to connect to MongoDB at %s", settings.MONGODB_URI)
            self.client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
            # Test ping with a quick timeout
            await asyncio.wait_for(self.client.admin.command('ping'), timeout=2.0)
            self.db = self.client[settings.DATABASE_NAME]
            self.is_connected = True
            logger.info("Successfully connected to MongoDB (%s)", settings.DATABASE_NAME)
        except Exception as e:
            logger.warning("MongoDB not available (%s). Initializing in-memory fallback mock database.", str(e))
            self.db = MockDatabase()
            self.is_connected = False

    async def close_database_connection(self):
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection.")

db_manager = DatabaseManager()

def get_database():
    if db_manager.db is None:
        db_manager.db = MockDatabase()
    return db_manager.db

# Collections helpers
def get_users_collection():
    return get_database()["users"]

def get_video_jobs_collection():
    return get_database()["video_jobs"]

def get_transcriptions_collection():
    return get_database()["transcriptions"]

def get_isl_conversions_collection():
    return get_database()["isl_conversions"]

def get_chat_sessions_collection():
    return get_database()["chat_sessions"]

def get_chat_messages_collection():
    return get_database()["chat_messages"]
