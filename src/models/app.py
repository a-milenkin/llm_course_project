from collections import defaultdict
from typing import Any

from aiohttp.web import Application
from telebot.async_telebot import AsyncTeleBot

from dao import DAO
from services import Services
from utils.similarity_search import SimilaritySearch


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class App(dict, metaclass=Singleton):
    """Global states and modules storage"""
    Dao: DAO
    Managers: Any
    WebApp: Application
    Services: Services
    Bot: AsyncTeleBot
    Tasks: dict
    Legend: SimilaritySearch
    # UserFile: SimilaritySearch

    def __init__(self):
        super().__init__()
        self["users_context"] = defaultdict(dict)

    def user_context(self, user_id: int) -> dict:
        """Context storage for every bot user"""
        return self["users_context"][user_id]
