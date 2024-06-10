import datetime
import random
import numpy as np
import string
import uuid
import asyncio
import csv
from dao.base import BaseDBDAO
from utils.structures import UserData


class UserDAO(BaseDBDAO):
    COLLECTION_NAME = "user"

    def __init__(self, app) -> None:
        super().__init__(app)

    async def async_init(self) -> None:
        await self.db[self.COLLECTION_NAME].create_index("user_id")

    async def create(self, data):
        await self.db[self.COLLECTION_NAME].insert_one(data)
        return data

    async def update(self, data):
        await self.db[self.COLLECTION_NAME].update_one({"user_id": data["user_id"]}, {"$set": data}, upsert=True)
        return data

    async def find_by_user_id(self, user_telegram_id: int) -> dict:
        return await self.db[self.COLLECTION_NAME].find_one({"user_id": user_telegram_id}, {"_id": 0})

    # async def find_all_by_user_id(self, user_telegram_id: int) -> dict:
    #     return self.db[self.COLLECTION_NAME].find({"user_id": user_telegram_id}, {"_id": 0})

    async def find_known_users_ids(self) -> set:
        return {
            int(obj["user_id"])
            async for obj in self.db[self.COLLECTION_NAME].find({}, {"user_id": 1})
        }

    async def find_users_without_renewed_premium(self):
        """
        returns a list of users who are about to renew their premium.
        either automatically or manually
        """
        return [obj async for obj in self.db[self.COLLECTION_NAME].find({
            "subscription": {"$eq": "premium"},
            "subscription_start_date": {
                "$lt": datetime.datetime.combine(datetime.datetime.utcnow(), datetime.time.min) - datetime.timedelta(days=30)
            }
        })]

    async def increment_generations(self, user_telegram_id: int):
        return await self.db[self.COLLECTION_NAME].update_one({"user_id": user_telegram_id},
                                                              {"$inc": {"generations": 1, "today_generations": 1}},
                                                              upsert=True)

    async def reset_today_generations(self, user_telegram_id: int):
        return await self.db[self.COLLECTION_NAME].update_many(
            {
                "user_id": user_telegram_id
            },
            {
                "$set": {
                    "today_generations": 0,
                    "last_generation_date": datetime.datetime.combine(datetime.datetime.utcnow(), datetime.time.min)}
            }
        )

    async def get_usage_in_interval(self, user_id, datetime1, datetime2):
        pipeline_total = [
            {"$unwind": "$messages"},
            {"$match": {
                "user_id": user_id,
                "messages.role": "user",
                "messages.created_at": {"$gte": datetime1, "$lte": datetime2}
            }},
            {"$group": {
                "_id": "$user_id",
                "talk_time": {"$sum": "$messages.voice_duration"}
            }},
            {"$limit": 1}
        ]
        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        user_result = [user async for user in users_cursor]
        user_result = user_result[0] if len(user_result) == 1 else {"talk_time": 0}
        user_talk_time_min = round(user_result["talk_time"] / 60, 1)
        return user_talk_time_min

    async def get_usage_by_weekday(self, user_id):
        """
        returns: {"mon": {"talk_time": 0}, "tue": {"talk_time": 0.1}, ...}
        weekdays: mon, tue, wen, thu, fri, sat, sun
        """
        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        # date -> datetime conversion
        week_start = datetime.datetime.combine(week_start, datetime.time.min)
        mon_start = week_start
        mon_end = mon_start + datetime.timedelta(days=1)
        mon = {"talk_time": await self.get_usage_in_interval(user_id, mon_start, mon_end)}

        tue_start = mon_end
        tue_end = tue_start + datetime.timedelta(days=1)
        tue = {"talk_time": await self.get_usage_in_interval(user_id, tue_start, tue_end)}

        wed_start = tue_end
        wed_end = wed_start + datetime.timedelta(days=1)
        wed = {"talk_time": await self.get_usage_in_interval(user_id, wed_start, wed_end)}

        thu_start = wed_end
        thu_end = thu_start + datetime.timedelta(days=1)
        thu = {"talk_time": await self.get_usage_in_interval(user_id, thu_start, thu_end)}

        fri_start = thu_end
        fri_end = fri_start + datetime.timedelta(days=1)
        fri = {"talk_time": await self.get_usage_in_interval(user_id, fri_start, fri_end)}

        sat_start = fri_end
        sat_end = sat_start + datetime.timedelta(days=1)
        sat = {"talk_time": await self.get_usage_in_interval(user_id, sat_start, sat_end)}

        sun_start = sat_end
        sun_end = sun_start + datetime.timedelta(days=1)
        sun = {"talk_time": await self.get_usage_in_interval(user_id, sun_start, sun_end)}

        return {
            "mon": mon,
            "tue": tue,
            "wen": wed,
            "thu": thu,
            "fri": fri,
            "sat": sat,
            "sun": sun
        }

    async def get_talk_time(self, user_id, interval="day", role = 'user'):
        """
        interval:
            day
            week
            month
            dialog - since the last time the user pressed /start
            total - 
        returns total time (in minutes) of user's voice messages that were sent not earlier than the start of the current <day>, <week> or <month>.
        """
        if interval != "dialog":
            today = datetime.date.today()
            if interval == "day":
                cutoff_date = today
            elif interval == "week":
                cutoff_date = today - datetime.timedelta(days=today.weekday())
            elif interval == "month":
                cutoff_date = today - datetime.timedelta(days=today.day)
            elif interval == "total":
                cutoff_date = today - datetime.timedelta(days=365 * 100)
            # convert date to datetime
            cutoff_date = datetime.datetime.combine(cutoff_date, datetime.time.min)
            pipeline_total = [
                {"$unwind": "$messages"},
                {"$match": {
                    "user_id": user_id,
                    "messages.role": role,
                    "messages.created_at": {"$gte": cutoff_date}
                }},
                {"$group": {
                    "_id": "$user_id",
                    "talk_time": {"$sum": "$messages.voice_duration"}
                }},
                {"$limit": 1}
            ]
        else:
            pipeline_total = [
                # Match documents with the specific user_id first to optimize the pipeline
                {
                    "$match": {
                        "user_id": user_id
                    }
                },
                # Add a field that will hold the array of messages starting from first_message_index
                {
                    "$addFields": {
                        "filtered_messages": {
                            "$slice": [
                                "$messages", "$first_message_index", {"$size": "$messages"}
                            ]
                        }
                    }
                },
                # Unwind the filtered messages
                {
                    "$unwind": "$filtered_messages"
                },
                # Match to filter only messages where role is "user"
                {
                    "$match": {
                        "filtered_messages.role": "user"
                    }
                },
                # Group by user_id and sum the voice durations
                {
                    "$group": {
                        "_id": "$user_id",
                        "talk_time": {"$sum": "$filtered_messages.voice_duration"}
                    }
                }
            ]

        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        user_result = [user async for user in users_cursor]
        user_result = user_result[0] if len(user_result) == 1 else {"talk_time": 0}
        user_talk_time_min = round(user_result["talk_time"] / 60, 1)
        return user_talk_time_min

######

    async def get_user_csv(self):
        """
        """

        pipeline_total = [
            {"$unwind": "$messages"},
            {"$match": {
                # "user_id": user_id,
                # "messages.role": "user",
                
            }},
            # {"$group": {
            #     "_id": "$user_id",
            #     "talk_time": {"$sum": "$messages.voice_duration"}
            # }},
            # {"$limit": 1}
        ]

 

        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        data = [user async for user in users_cursor]
        
        print('Creating a CSV file')
        # Create a CSV file
        with open("output.csv", "w", newline="", encoding="utf-8") as csv_file:
            # Write the field names to the first line of the CSV file
            field_names = ['last_generation_date', 'payments_data', 'reminders', 'reminder_enable', 'bot_role', 'bot_state', 'username', 
                            'email', 'preferences', 'today_generations', 'user_id', 'stuck_reminder_enabled', 'subscription',
                              'first_message_index', '_id', 'temp_data', 'generations', 'subscription_start_date', 'messages']
            writer = csv.DictWriter(csv_file, fieldnames=field_names)
            # writer.writeheader()

            # Iterate over the query results
            for doc in data:
                # Write the field values to the CSV file
                row = doc# {"field_name_1": doc["field_name_1"], "field_name_2": doc["field_name_2"], "field_name_3": doc["field_name_3"]}
                writer.writerow(row)


    async def get_new_users_by_interval(self, interval='day'):
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
                "subscription_start_date": {"$gte": datetime.datetime.combine(cutoff_date, datetime.time.min)}
            }},
            {"$count": "user_count"}
        ]

        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        user_result = [user async for user in users_cursor]

        user_result = user_result[0] if len(user_result) == 1 else {"user_count": 0}
        return user_result["user_count"]

    async def get_users_speaking_duration(self, interval='day'):

        """
        interval:
            day, week, month, total - 
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
            {"$unwind": "$messages"},
            {"$match": {"messages.role": "user",
                        "messages.created_at": {"$gte": datetime.datetime.combine(cutoff_date, datetime.time.min)}}},
            {"$group": {"_id": None,
                        "talk_time_sum": {"$sum": "$messages.voice_duration"},
                        "talk_time_avg": {"$avg": "$messages.voice_duration"}}},
        ]

        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        result = [user async for user in users_cursor]

        result[0]["talk_time_sum"] = round(result[0]["talk_time_sum"] / 60, 2)
        result[0]["talk_time_avg"] = round(result[0]["talk_time_avg"], 1)

        # convert date to datetime
        pipeline_total = [
            {"$unwind": "$messages"},
            {"$match": {"messages.role": "assistant",
                        "messages.created_at": {
                            "$gte": datetime.datetime.combine(cutoff_date, datetime.time.min)
                        }}},
            {"$group": {"_id": None,
                        "talk_time_bot_sum": {"$sum": "$messages.voice_duration"},
                        "talk_time_bot_avg": {"$avg": "$messages.voice_duration"}}},
        ]

        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        result2 = [user async for user in users_cursor]

        result[0]["talk_time_bot_sum"] = round(result2[0]["talk_time_bot_sum"] / 60, 2)
        result[0]["talk_time_bot_avg"] = round(result2[0]["talk_time_bot_avg"], 1)

        return result[0]

    async def get_general_bottle_days(self, interval='day', user_id=None):

        """
        interval: day, week, month, total - 
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

  
        pipeline_total = []
        pipeline_total.append({"$unwind": "$messages"})

        if user_id is None:
            pipeline_total.append({"$match": {
                "messages.role": "user", 
                "messages.created_at": {"$gte": datetime.datetime.combine(cutoff_date, datetime.time.min)}}})
        else:
            pipeline_total.append({"$match": {
                "user_id": user_id,
                "messages.role": "user", 
                "messages.created_at": {"$gte": datetime.datetime.combine(cutoff_date, datetime.time.min)}}})

        pipeline_total.append({"$addFields":{
            "day_of_year": {"$dayOfYear": "$messages.created_at"}}})
        
        pipeline_total.append({"$group": {
                "_id": {"user_id": "$user_id"},
                "unique_days": {"$addToSet": "$day_of_year"},
            }})

        pipeline_total.append({"$addFields": {"nuniq_days": {"$size": "$unique_days"}}})
        pipeline_total.append({"$group": {"_id": "$nuniq_days","active_users": {"$sum": 1},}})
        
        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        result = [user async for user in users_cursor]
        result_dict = {}
        for r in result:
            result_dict[r['_id']] = r['active_users']
        return result_dict

    async def get_general_funnel_voices(self, interval='day'):

        """
        interval:
            day, week, month, total - 
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
            # Filter messages to include only those where role is "user" or when array is empty
            {
                "$addFields": {
                    "user_messages": {
                        "$filter": {
                            "input": "$messages",
                            "as": "message",
                            "cond": {"$eq": ["$$message.role", "user"]}
                        }
                    }
                }
            },
            # Add the user_messages_count field which holds the number of user messages
            {
                "$addFields": {
                    "user_messages_count": {"$size": "$user_messages"}
                }
            },
            # Handle possible non-existent 'messages' field by setting count to 0
            {
                "$addFields": {
                    "user_messages_count": {
                        "$cond": {
                            "if": {"$isArray": "$messages"},
                            "then": "$user_messages_count",
                            "else": 0
                        }
                    }
                }
            },
            # Group the documents by user_messages_count and sum the occurrences
            {
                "$group": {
                    "_id": "$user_messages_count",
                    "user_count": {"$sum": 1},
                }
            },
        ]

        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        result = [user async for user in users_cursor]
        # print('result', result[:30])

        result_dict = {}
        for r in result:
            result_dict[r['_id']] = r['user_count']
        result_dict = dict(sorted(result_dict.items(), key=lambda item: item[0]))

        all_vals = sum([[k]*v for k, v in result_dict.items() if k !=0], [])
        median_voice = np.median(all_vals)

        users_sum = np.sum(list(result_dict.values()))
        # print('result_dict', result_dict)

        cum_result_dict = result_dict.copy()
        sorted_key = sorted(list(result_dict.keys()))  # [::-1]
        # print('sorted_key', sorted_key)        

        cum_result_dict[-1] = 0
        for i, voice_num in enumerate(sorted(sorted_key)):
            cum_result_dict[voice_num] += cum_result_dict[sorted_key[i - 1]]
        del cum_result_dict[-1]

        # print('cum_result_dict', cum_result_dict)      

        return cum_result_dict, median_voice, users_sum

    async def get_users_top(self, user_telegram_id: int, top_n=10):
        today = datetime.date.today()
        last_monday = today - datetime.timedelta(days=today.weekday())
        # convert date to datetime
        last_monday = datetime.datetime.combine(last_monday, datetime.time.min)
        pipeline_total = [
            {"$unwind": "$messages"},
            {"$match": {
                "messages.role": "user",
                "messages.created_at": {"$gte": last_monday}
            }},
            {"$group": {
                "_id": "$user_id",
                "talk_time": {"$sum": "$messages.voice_duration"},
                "username": {"$first": "$username"}
            }},
            {"$sort": {"talk_time": -1}}
        ]

        users_cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline_total)
        users_sorted = [user async for user in users_cursor]

        users_top = users_sorted[:top_n]

        users_top_formatted = []
        for user in users_top:
            users_top_formatted.append({
                'id': user["_id"],
                'name': user.get('username', 'Unknown'),
                'talk_time': round(user.get('talk_time', 0) / 60, 1)
            })
        user_position = next(
            (index + 1 for index, user in enumerate(users_sorted) if user["_id"] == user_telegram_id), len(users_sorted)
        )
        
        user_talk_time_sec = next((u for u in users_sorted if u["_id"] == user_telegram_id), {"talk_time": 0})["talk_time"]
        user_talk_time_min = round(user_talk_time_sec / 60, 1)

        return users_top_formatted, user_position, user_talk_time_min

    async def create_random_users(self, count=2000):
        for _ in range(count):
            user_data = generate_random_user()
            await self.create(user_data.__dict__)

    async def get_avg_voice_messages_count(self, user_id: int, interval: str):
        today = datetime.date.today()
        if interval == "day":
            cutoff_date = today
        elif interval == "week":
            cutoff_date = today - datetime.timedelta(days=today.weekday())
        elif interval == "month":
            cutoff_date = today - datetime.timedelta(days=today.day)
        else:
            raise ValueError("interval must be 'day', 'week', 'month'")
        # convert date to datetime
        cutoff_date = datetime.datetime.combine(cutoff_date, datetime.time.min)
        pipeline = [
            {"$unwind": "$messages"},
            {"$match": {
                "user_id": user_id,
                "messages.role": "user",
                "messages.created_at": {"$gte": cutoff_date}
            }},
            {"$group": {
                "_id": "$user_id",
                "voice_count": {"$sum": 1}
            }},
            {"$limit": 1}
        ]

    async def get_campaign_stats(self):

        # convert date to datetime
        pipeline = [

            {"$group": {
                "_id": "$utm_campaign",
                "campaign_users": {"$sum": 1}
            }},
        
        ]

        cursor = self.db[self.COLLECTION_NAME].aggregate(pipeline)
        result = [doc async for doc in cursor]

        result_dict = {}
        for r in result:
            result_dict[r["_id"]] = r["campaign_users"] 

        return result_dict

    async def _check_field_exist(self, field_name):
        document = await self.db[self.COLLECTION_NAME].find_one({field_name: {"$exists": True}})
        return document is not None

    async def add_new_field(self, field_name, default_value=None):
        if not self._check_field_exist(field_name):
            await self.db[self.COLLECTION_NAME].update_many({}, {"$set": {field_name: default_value}})

    async def add_new_user_messages_field(self, field_name, default_value=None):
        # Обновить каждый словарь внутри списка, добавив новое поле с заданным значением
        update_script = {"$set": {f"messages.$[elem].{field_name}": default_value}}
        # Применить обновление только к элементам, где нет нового поля
        array_filters = [{f"elem.{field_name}": {"$exists": False}, "elem.role": "user"}]
        await self.db[self.COLLECTION_NAME].update_many({}, update_script, array_filters=array_filters)


def generate_random_user():
    user = UserData(
        user_id=random.randint(1, 100000),
        username=''.join(random.choices(string.ascii_letters, k=10)),
        subscription=random.choice(['free', 'premium']),
        email=None if random.choice([True, False]) else ''.join(
            random.choices(string.ascii_letters + string.digits, k=10)) + "@example.com",
        subscription_start_date=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(0, 365)),
        generations=random.randint(0, 100),
        today_generations=random.randint(0, 100),
        last_generation_date=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(0, 365)),
        messages=[{
            "role": random.choice(["user", "assistant"]),
            "content": ''.join(
                random.choices(string.ascii_letters + string.digits + string.punctuation, k=random.randint(10, 100))),
            "voice_file_id": str(uuid.uuid4()),
            "voice_duration": random.uniform(0.0, 60.0),
            "created_at": datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(0, 365))
        } for _ in range(random.randint(0, 100))],
        payments_data={"payment_id": None},
        preferences={"sub_autoextend": random.choice([True, False])},
        bot_state="default",
        temp_data={}
    )

    return user
