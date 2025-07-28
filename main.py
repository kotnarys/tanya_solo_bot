import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers import start, info, tariffs, support, payment
from auto_spam import start_auto_spam_task

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    
    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализация диспетчера
    dp = Dispatcher()
    
    # Подключение роутеров
    dp.include_router(start.router)
    dp.include_router(info.router)
    dp.include_router(tariffs.router)
    dp.include_router(support.router)
    dp.include_router(payment.router)
    
    # Запуск фоновой задачи автоспама
    logger.info("🚀 Запускаем фоновую задачу автоспама...")
    auto_spam_task = asyncio.create_task(start_auto_spam_task(bot))
    logger.info("✅ Фоновая задача автоспама создана")
    
    # Запуск бота
    logger.info("Бот запускается...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        # Отменяем фоновую задачу
        logger.info("🛑 Останавливаем фоновую задачу автоспама...")
        auto_spam_task.cancel()
        try:
            await auto_spam_task
        except asyncio.CancelledError:
            logger.info("✅ Фоновая задача автоспама остановлена")
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())