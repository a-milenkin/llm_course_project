class BaseDAO:
    def __init__(self, app) -> None:
        pass

    async def async_init(self) -> None:
        return


class BaseDBDAO(BaseDAO):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.db_manager = app.Managers.db_manager
        self.db = self.db_manager.db

    async def async_init(self) -> None:
        return


class BaseSessionDAO(BaseDAO):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.session_manager = app.Managers.session_manager
