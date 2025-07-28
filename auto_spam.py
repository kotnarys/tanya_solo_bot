import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto
from keyboards.inline import get_avatar_info_menu, get_helps_menu, get_reviews_menu, get_tariffs_menu
from config import TEXTS, IMAGES, REVIEWS_IMAGES
from promo_utils import get_tariffs_text_with_promo
from database import db

# Словарь для отслеживания последней активности пользователей
user_last_activity = {}

# Словарь для отслеживания какой этап автоспама для каждого пользователя
# 0 - не начат, 1 - отправлен "что такое аватар", 2 - "с чем помогает", 3 - "отзывы", 4 - "тарифы" (завершен)
user_spam_stage = {}

def update_user_activity(user_id: int):
    """
    Обновляет время последней активности пользователя и ОТКЛЮЧАЕТ автоспам навсегда
    
    Args:
        user_id: ID пользователя
    """
    current_time = datetime.now()
    user_last_activity[user_id] = current_time
    
    # НАВСЕГДА отключаем автоспам для этого пользователя в БД
    db.mark_spam_completed(user_id)

def update_user_activity_start_only(user_id: int):
    """
    Обновляет активность ТОЛЬКО для /start (не отключает автоспам)
    
    Args:
        user_id: ID пользователя
    """
    current_time = datetime.now()
    user_last_activity[user_id] = current_time
    
    # Сбрасываем этап автоспама на 0, но НЕ отключаем в БД
    user_spam_stage[user_id] = 0

async def send_next_spam_message(bot: Bot, user_id: int, stage: int):
    """
    Отправляет следующее сообщение автоспама в зависимости от этапа
    
    Args:
        bot: экземпляр бота
        user_id: ID пользователя  
        stage: этап автоспама (1-4)
    """
    try:
        if stage == 1:
            # 1. Что такое онлайн-аватар
            image_path = IMAGES["what_is_avatar"]
            
            if os.path.exists(image_path):
                photo = FSInputFile(image_path)
                await bot.send_photo(
                    user_id,
                    photo,
                    caption=TEXTS["what_is_avatar"],
                    reply_markup=get_avatar_info_menu()
                )
            else:
                await bot.send_message(
                    user_id,
                    TEXTS["what_is_avatar"], 
                    reply_markup=get_avatar_info_menu()
                )
            
        elif stage == 2:
            # 2. С чем помогает
            image_path = IMAGES["what_helps"]
            
            if os.path.exists(image_path):
                photo = FSInputFile(image_path)
                await bot.send_photo(
                    user_id,
                    photo,
                    caption=TEXTS["what_helps"],
                    reply_markup=get_helps_menu()
                )
            else:
                await bot.send_message(
                    user_id,
                    TEXTS["what_helps"], 
                    reply_markup=get_helps_menu()
                )
            
        elif stage == 3:
            # 3. Отзывы
            # Отправляем текст отзывов
            await bot.send_message(
                user_id,
                TEXTS["reviews"], 
                reply_markup=get_reviews_menu()
            )
            
            # Отправляем фотографии отзывов
            media_group = []
            for image_path in REVIEWS_IMAGES:
                if os.path.exists(image_path):
                    try:
                        file_size = os.path.getsize(image_path)
                        max_size = 10 * 1024 * 1024  # 10 МБ
                        
                        if file_size <= max_size:
                            photo = FSInputFile(image_path)
                            media_group.append(InputMediaPhoto(media=photo))
                    except Exception:
                        pass
            
            if media_group:
                # Разбиваем на группы по 10 фотографий
                chunk_size = 10
                for i in range(0, len(media_group), chunk_size):
                    chunk = media_group[i:i + chunk_size]
                    await bot.send_media_group(user_id, chunk)
                    
                    if i + chunk_size < len(media_group):
                        await asyncio.sleep(0.5)
            
        elif stage == 4:
            # 4. Тарифы - финальное сообщение
            image_path = IMAGES["tariffs"]
            text = get_tariffs_text_with_promo()
            
            if os.path.exists(image_path):
                photo = FSInputFile(image_path)
                await bot.send_photo(
                    user_id,
                    photo,
                    caption=text,
                    reply_markup=get_tariffs_menu()
                )
            else:
                await bot.send_message(
                    user_id,
                    text, 
                    reply_markup=get_tariffs_menu()
                )
            
            # Отмечаем в базе данных, что спам завершен
            db.mark_spam_completed(user_id)
            
    except Exception:
        pass

async def start_auto_spam_task(bot: Bot):
    """
    Запускает фоновую задачу для отправки автосообщений
    
    Args:
        bot: экземпляр бота
    """
    while True:
        try:
            current_time = datetime.now()
            
            # Создаем копию словаря для безопасной итерации
            if user_last_activity:
                # Копируем словарь, чтобы избежать "dictionary changed size during iteration"
                users_snapshot = dict(user_last_activity)
                
                for user_id, last_activity in users_snapshot.items():
                    time_diff = current_time - last_activity
                    minutes_since_activity = int(time_diff.total_seconds() // 60)
                    
                    # Проверяем, был ли уже ПОЛНОСТЬЮ завершен/отключен спам в БД
                    if db.is_spam_completed(user_id):
                        continue
                    
                    # Получаем текущий этап спама для пользователя
                    current_stage = user_spam_stage.get(user_id, 0)
                    
                    # Каждая минута неактивности = следующий этап
                    needed_stage = min(minutes_since_activity, 4)
                    
                    # Если пользователь неактивен достаточно долго и нужно отправить следующий этап
                    if needed_stage > current_stage and needed_stage <= 4:
                        await send_next_spam_message(bot, user_id, needed_stage)
                        user_spam_stage[user_id] = needed_stage
            
        except Exception:
            pass
        
        # Проверяем каждые 10 секунд
        await asyncio.sleep(10)