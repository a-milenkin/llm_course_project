from pymongo import MongoClient
import datetime

username = "gaim"
password = "gaim_mongo_P4ssw0rd_s6d5f"
host = "localhost"
port = "27018"
dbname = "gaim_db"

client = MongoClient(f'mongodb://{username}:{password}@{host}:{port}/')
db = client[dbname]
user_collection = db['user']

# for user in user_collection.find():
#     messages = user.get('messages')
#     if isinstance(messages, list):
#         continue
#     else:
#         print(messages)
#         print(user)

#result = user_collection.delete_one({'user_id': -1002001935818})
#if result.deleted_count > 0:
#    print(f"Объект с user_id={-1002001935818} был удален.")
#else:
#    print(f"Объект с user_id={-1002001935818} не найден.")

#result = user_collection.update_one(
#    {'user_id': 5654127663},
#    {'$set': {'subscription': 'premium'}}
#)
#
#print(f"Количество обновленных документов: {result.modified_count}")

#result = user_collection.find_one({'user_id': 710434143}, {'_id': 0})

