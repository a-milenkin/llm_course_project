# tg_bot_template
https://t.me/GoshaSpeakBot
### Project structure

```  
├───grafana_exporter                 # Custom mongo data export
├───nginx-data                       # Nginx config
├───docker-compose.yaml        
├───.env.example                     # Docker compose config file example  
└───src
    ├───assets                       # Place any icons, assets, mediafiles here
    ├───dao                          # Place any external services handlers here
    │   └───__init__.py              # Dao namespace class here. Dont forget do add created module 
    │   └───base.py                  # Base interface. Every DAO class should be derived from it  
    │   └───example.py               # Example dao shows how to use mongodb collection
    │
    ├───managers                     # Low-level external connections handlers here
    │   └───__init__.py              # Managers namespace class here. Dont forget do add created module 
    │   └───database.py              # Mongodb connector
    │   └───session.py               # Any persistent sessions for web requests
    │   └───states.py                # Default telebot groups/states extension
    │
    ├───models                       # Place any model classes here: object data sctuctures, system classes, db models
    │   └───app.py                   # Global App singleton, inherits dict. Use it to access modules and save/share context
    │
    ├───mongo_migrations             # Scripts for db consistency
    │   └───
    │
    ├───routes                       # Place telegram endpoint handlers here. 
    │   └───example.py               # Example telegram bot endpoint
    │
    ├───services                     # Place any non-bot logic and modules here
    │   └───__init__.py              # Services namespace class here. Dont forget do add created module 
    │
    ├───utils                        # Place any helpers here
    │   └───
    │
    ├───config.yaml                  # Bot config file. Access it with App()["config"]
    ├───filters.py                   # PyTelegramBotApi based filters
    ├───main.py                      # Start point. System init and routes listing 
    ├───settings.py                  # Config file parsing
    └───swagger.yaml                 # web api docs

```
# Запуск
``sudo docker compose up -d --build``
# Запуск после билда
``docker compose start``
# Выключение
``docker compose stop``
