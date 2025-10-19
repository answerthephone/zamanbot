Example .env:

```
BOT_TOKEN=bot_token
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}
DB_USER=postgres
DB_PASSWORD=12345678
DB_HOST=zamanbot_db
DB_PORT=5432
DB_NAME=clients_db
OPENAI_API_KEY=your_openai_api_key
```

Docker:

````
sudo docker-compose up --build
````
