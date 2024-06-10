# Для получения session_string
#
# import os
#
# from dotenv import load_dotenv
# from pyrogram import Client
#
# load_dotenv('test.env')
#
# api_id = os.getenv('API_ID')
# api_hash = os.getenv('API_HASH')
# session_string = os.getenv('SESSION_STRING_TEST')
#
# with Client("my_account", session_string=session_string, api_id=api_id, api_hash=api_hash, test_mode=True) as app:
#     print(app.export_session_string())
