import asyncio
import logging
import aiohttp
import json
from core.config import GETCOURSE_REFERRAL_WEBHOOK

logger = logging.getLogger(__name__)

async def send_referral_data_to_getcourse(email: str, quantity: int):
    """
    Отправляет данные о реферальном балансе в GetCourse
    
    Args:
        email: Email пользователя
        quantity: Текущий баланс пользователя
    """
    try:
        data = {
            "email": email,
            "quantity": quantity
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GETCOURSE_REFERRAL_WEBHOOK, 
                json=data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"Данные реферальной системы отправлены в GetCourse для {email}: {quantity}")
                    return True
                else:
                    logger.error(f"Ошибка отправки в GetCourse: {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        logger.error("Timeout при отправке данных в GetCourse")
        return False
    except Exception as e:
        logger.error(f"Ошибка отправки данных в GetCourse: {e}")
        return False

def send_referral_data_sync(email: str, quantity: int):
    """Синхронная версия для использования в обычных функциях"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если уже в event loop, создаем задачу
            asyncio.create_task(send_referral_data_to_getcourse(email, quantity))
        else:
            # Если нет активного loop, запускаем синхронно
            asyncio.run(send_referral_data_to_getcourse(email, quantity))
    except Exception as e:
        logger.error(f"Ошибка синхронной отправки в GetCourse: {e}")