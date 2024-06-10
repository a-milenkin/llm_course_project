from models.app import App
from utils.structures import UserData
import datetime


async def migrate_users():
    print("migrating users...")
    for user_id in await App().Dao.user.find_known_users_ids():
        try:
            data = await App().Dao.user.find_by_user_id(user_id)
            user = UserData(**data)
            await App().Dao.user.update({
                        "user_id": user_id,
                        'utm_campaign' : None,
                    })
        except Exception as e:
            print('exception while migrating user', user_id)
            raise e
    print("done migrating users")
