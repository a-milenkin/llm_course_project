import datetime

from dao.base import BaseDBDAO


class PaymentsDAO(BaseDBDAO):
    COLLECTION_NAME = "payments"

    def __init__(self, app) -> None:
        super().__init__(app)

    async def async_init(self) -> None:
        await self.db[self.COLLECTION_NAME].create_index("payment_id")

    async def create(self, data):
        await self.db[self.COLLECTION_NAME].insert_one(data)
        return data

    async def update(self, data):
        await self.db[self.COLLECTION_NAME].update_one({"payment_id": data["payment_id"]}, {"$set": data}, upsert=True)
        return data

    async def find_by_payment_id(self, payment_id: str) -> dict:
        return await self.db[self.COLLECTION_NAME].find_one({"payment_id": payment_id}, {"_id": 0})

    async def find_last_payment_of_user(self, user_id: int, product="premium") -> dict:
        result = [obj async for obj in self.db[self.COLLECTION_NAME].find({"user_id": user_id, "product": product}, {"_id": 0}).sort("created_at", -1).limit(1)]
        return result[0] if result else None
    
    async def find_known_payments(self) -> set:
        return {
            int(obj["user_id"])
            async for obj in self.db[self.COLLECTION_NAME].find({}, {"user_id": 1})
        }
    
    async def get_new_payments_by_interval(self, interval='day'):
        """
        interval:
            day
            week
            month
            total - 
        returns total time (in minutes) of user's voice messages that were sent not earlier than the start of the current <day>, <week> or <month>.
        """

        today = datetime.date.today()
        if interval == "day":
            cutoff_date = today
        elif interval == "week":
            cutoff_date = today - datetime.timedelta(days=today.weekday())
        elif interval == "month":
            cutoff_date = today - datetime.timedelta(days=today.day)
        elif interval == "30days":
            cutoff_date = today - datetime.timedelta(days=30)
        elif interval == "total":
            cutoff_date = today - datetime.timedelta(days=365 * 100)

        # convert date to datetime
        pipeline_total = [
            {"$match": {
                "created_at": {"$gte": datetime.datetime.combine(cutoff_date, datetime.time.min)}
            }},
            {"$count": "user_count"}
        ]

        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        user_result = [user async for user in users_cursor]
         
        user_result = user_result[0] if len(user_result) == 1 else {"user_count": 0}
        return user_result["user_count"]