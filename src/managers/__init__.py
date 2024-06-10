from dataclasses import dataclass

from managers.database import DatabaseManager
from managers.session import SessionManager


@dataclass
class Managers:
    db_manager: DatabaseManager
    session_manager: SessionManager


async def setup_managers(app):
    app.Managers = Managers(
        db_manager=DatabaseManager(app["config"]),
        session_manager=SessionManager(app["config"])
    )
    await app.Managers.db_manager.connect()
