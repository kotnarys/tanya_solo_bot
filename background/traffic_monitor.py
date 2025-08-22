#!/usr/bin/env python3
"""
Фоновая задача для мониторинга трафика и создания суточных отчетов
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from aiogram import Bot
from core.database import db
from core.config import ADMIN_IDS

logger = logging.getLogger(__name__)

async def send_daily_report(bot: Bot):
    """
    Отправляет суточный отчет по трафику администраторам
    """
    try:
        report = db.get_daily_report()
        
        # Отправляем отчет всем админам
        admin_ids = [int(admin_id) for admin_id in ADMIN_IDS.split(',') if admin_id.strip()]
        
        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, report)
                logger.info(f"Суточный отчет отправлен админу {admin_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки отчета админу {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка создания суточного отчета: {e}")

async def traffic_monitor_task(bot: Bot):
    """
    Основная задача мониторинга трафика
    Отправляет суточные отчеты в 9:00 MSK каждый день
    """
    logger.info("Запущена задача мониторинга трафика")
    
    while True:
        try:
            # Московское время (UTC+3)
            current_time = datetime.now()
            
            # Проверяем, нужно ли отправить суточный отчет (в 9:00)
            if current_time.hour == 9 and current_time.minute == 0:
                logger.info("Время отправки суточного отчета")
                await send_daily_report(bot)
                
                # Ждем минуту, чтобы не отправлять отчет дважды
                await asyncio.sleep(60)
            
            # Каждый час обновляем статистику активных пользователей
            if current_time.minute == 0:
                try:
                    # Подсчитываем активных пользователей за последние 24 часа
                    # (это можно улучшить, добавив таблицу активности)
                    logger.debug("Обновление почасовой статистики")
                except Exception as e:
                    logger.error(f"Ошибка обновления почасовой статистики: {e}")
            
            # Проверяем каждые 30 секунд
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Ошибка в задаче мониторинга трафика: {e}")
            await asyncio.sleep(60)

async def send_test_report(bot: Bot, admin_id: int):
    """
    Отправляет тестовый отчет конкретному администратору
    """
    try:
        report = db.get_daily_report()
        await bot.send_message(admin_id, f"🧪 ТЕСТОВЫЙ ОТЧЕТ:\n\n{report}")
        logger.info(f"Тестовый отчет отправлен админу {admin_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки тестового отчета: {e}")
        return False