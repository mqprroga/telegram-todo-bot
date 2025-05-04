import asyncio
from app.bot import TodoBot
from app.main import app
import uvicorn
import os

async def main():
    # Запуск FastAPI
    server = uvicorn.Server(
        config=uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    )
    
    # Запуск бота
    bot = TodoBot(os.getenv("TELEGRAM_TOKEN"))
    
    # Запускаем оба сервиса параллельно
    await asyncio.gather(
        server.serve(),
        asyncio.to_thread(bot.run)
    )

if __name__ == "__main__":
    asyncio.run(main())