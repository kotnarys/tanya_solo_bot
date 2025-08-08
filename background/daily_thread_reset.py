import asyncio
import logging
from datetime import datetime, time
import pytz
from core.database import db

logger = logging.getLogger(__name__)

async def daily_thread_reset_task():
    """
    Фоновая задача для ежедневного сброса OpenAI threads в 00:00 по московскому времени
    """
    moscow_tz = pytz.timezone('Europe/Moscow')
    
    logger.info("🔄 Фоновая задача ежедневного сброса threads запущена")
    
    while True:
        try:
            # Получаем текущее время в Москве
            now_moscow = datetime.now(moscow_tz)
            
            # Определяем время следующего сброса (00:00)
            from datetime import timedelta
            
            next_reset_time = now_moscow.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            # Если уже прошло 00:00 сегодня, планируем на завтра
            if now_moscow.time() >= time(0, 1):  # Если прошла минута после полуночи
                next_reset_time = next_reset_time + timedelta(days=1)
            
            # Вычисляем время ожидания до следующего сброса
            wait_seconds = (next_reset_time - now_moscow).total_seconds()
            
            logger.info(f"⏰ Следующий сброс threads запланирован на {next_reset_time.strftime('%Y-%m-%d %H:%M:%S %Z')} (через {wait_seconds/3600:.1f} часов)")
            
            # Ждем до времени сброса
            await asyncio.sleep(wait_seconds)
            
            # Выполняем ежедневный сброс
            logger.info("🔄 Выполняется ежедневный сброс OpenAI threads...")
            deleted_count = db.reset_all_threads_daily()
            
            if deleted_count > 0:
                logger.info(f"✅ Ежедневный сброс завершен: удалено {deleted_count} threads")
            else:
                logger.info("✅ Ежедневный сброс завершен: нет threads для удаления")
                
        except Exception as e:
            logger.error(f"❌ Ошибка в задаче ежедневного сброса threads: {e}")
            # При ошибке ждем час перед повторной попыткой
            await asyncio.sleep(3600)

def get_next_reset_time():
    """
    Возвращает время следующего сброса threads в московском времени
    """
    moscow_tz = pytz.timezone('Europe/Moscow')
    now_moscow = datetime.now(moscow_tz)
    
    # Следующий сброс в 00:00
    if now_moscow.time() < time(0, 1):  # Если еще не прошла минута после полуночи
        next_reset = now_moscow.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Сброс завтра в 00:00
        tomorrow = now_moscow.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        next_reset = tomorrow + timedelta(days=1)
    
    return next_reset