from dataclasses import dataclass

from dao.base import BaseDAO
from dao.sd_ndt_dao import ControlnetClientDAO
from dao.user_dao import UserDAO
from dao.payments_dao import PaymentsDAO


# DAO namespace. List any BaseDAO derived here
@dataclass
class DAO:
    user: UserDAO
    sd_controlnet: ControlnetClientDAO
    payments: PaymentsDAO

    @property
    def dao_list(self) -> list[BaseDAO]:
        return list(filter(lambda dao: isinstance(dao, BaseDAO), self.__dict__.values()))


async def setup_dao(app):
    app.Dao = DAO(
        user=UserDAO(app),
        sd_controlnet=ControlnetClientDAO(app),
        payments=PaymentsDAO(app)
    )

    for dao in app.Dao.dao_list:
        await dao.async_init()
