import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.client: Optional[AsyncIOMotorClient] = None

    async def connect(self):
        if self.config["mongodb"].get("connection_string"):
            self.client = AsyncIOMotorClient(self.config["mongodb"]["connection_string"])
        else:
            self.client = AsyncIOMotorClient(
                host=self.config["mongodb"]["host"],
                port=self.config["mongodb"]["port"],
                username=self.config["mongodb"]["user"],
                password=self.config["mongodb"]["password"],
                authSource="admin",
            )
        await self.client.admin.command({"ping": 1})
        logger.info("Database connected")

    def __getattr__(self, item):
        if item == "db":
            return self.client[self.config["mongodb"]["name"]]
        return self.__dict__[item]

    async def disconnect(self):
        self.client.close()
        logger.info("Database disconnected")
