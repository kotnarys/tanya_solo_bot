import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from keyboards.inline import get_avatar_info_menu, get_helps_menu, get_reviews_menu, get_tariffs_menu
from core.config import TEXTS, IMAGES, REVIEWS_IMAGES
from core.database import db
from utils.message_utils import send_split_message
import logging

logger = logging.getLogger(__name__)

# Словарь для отслеживания последней активности пользователей
user_last_activity = {}

# Словарь для отслеживания какой этап автоспама для каждого пользователя
# 0 - не начат, 1 - "2 super novosti", 2 - "что такое аватар", 3 - "с чем помогает", 4 - "отзывы", 5 - "тарифы" (завершен)
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

async def send_video_with_cache(bot: Bot, user_id: int, video_path: str) -> bool:
    """
    Отправляет видео с использованием кэша file_id
    """
    try:
        file_size = os.path.getsize(video_path)
        max_size = 50 * 1024 * 1024  # 50 МБ
        
        if file_size > max_size:
            logger.warning(f"Видео слишком большое: {file_size / 1024 / 1024:.1f} МБ")
            return False
        
        # Проверяем кэшированный file_id
        cached_file_id = db.get_media_file_id(video_path)
        
        if cached_file_id:
            # Используем кэшированный file_id
            await bot.send_video_note(user_id, cached_file_id, request_timeout=30)
            db.log_traffic("auto_spam_video_cached", user_id, "video_note", 100, video_path)
            db.update_daily_stats(total_media_sent=1, total_bytes_sent=100)
            logger.info(f"Видео отправлено через file_id пользователю {user_id}")
        else:
            # Первая отправка - загружаем файл
            video = FSInputFile(video_path)
            message = await bot.send_video_note(user_id, video, request_timeout=120)
            
            # Сохраняем file_id
            if message.video_note:
                db.save_media_file_id(video_path, message.video_note.file_id, "video_note", file_size)
                logger.info(f"Видео отправлено и file_id сохранен для {video_path}")
            
            db.log_traffic("auto_spam_video_upload", user_id, "video_note", file_size, video_path)
            db.update_daily_stats(total_media_sent=1, total_bytes_sent=file_size)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки видео: {e}")
        return False

async def send_photo_with_cache(bot: Bot, user_id: int, image_path: str, caption: str = None, reply_markup=None) -> bool:
    """
    Отправляет фото с использованием кэша file_id
    """
    try:
        file_size = os.path.getsize(image_path)
        
        # Проверяем кэшированный file_id
        cached_file_id = db.get_media_file_id(image_path)
        
        if cached_file_id:
            # Используем кэшированный file_id
            await bot.send_photo(user_id, cached_file_id, caption=caption, reply_markup=reply_markup)
            db.log_traffic("auto_spam_photo_cached", user_id, "photo", 100, image_path)
            db.update_daily_stats(total_media_sent=1, total_bytes_sent=100)
            logger.info(f"Фото отправлено через file_id пользователю {user_id}")
        else:
            # Первая отправка - загружаем файл
            photo = FSInputFile(image_path)
            message = await bot.send_photo(user_id, photo, caption=caption, reply_markup=reply_markup)
            
            # Сохраняем file_id
            if message.photo:
                db.save_media_file_id(image_path, message.photo[-1].file_id, "photo", file_size)
                logger.info(f"Фото отправлено и file_id сохранен для {image_path}")
            
            db.log_traffic("auto_spam_photo_upload", user_id, "photo", file_size, image_path)
            db.update_daily_stats(total_media_sent=1, total_bytes_sent=file_size)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        return False

async def send_next_spam_message(bot: Bot, user_id: int, stage: int):
    """
    Отправляет следующее сообщение автоспама в зависимости от этапа
    
    Args:
        bot: экземпляр бота
        user_id: ID пользователя  
        stage: этап автоспама (1-5)
    """
    try:
        # Проверяем, не заблокировал ли пользователь бота
        if db.is_user_blocked(user_id):
            logger.debug(f"Пользователь {user_id} в черном списке, пропускаем автоспам")
            return
        
        if stage == 1:
            # 1. 2 Super Novosti - отправляем видео кружок и текст
            try:
                # Читаем текст из файла
                text_path = "media/video/2_super_novosti.txt"
                if os.path.exists(text_path):
                    with open(text_path, 'r', encoding='utf-8') as f:
                        text_content = f.read().strip()
                else:
                    text_content = "😍 2 супер новости"
                
                # Отправляем видео кружок
                video_path = "media/video/2_super_novosti.mp4"
                if os.path.exists(video_path):
                    await send_video_with_cache(bot, user_id, video_path)
                
                # Отправляем текст отдельно
                await send_split_message(bot, text_content, user_id)
                db.log_traffic("auto_spam_text", user_id, "text", len(text_content.encode('utf-8')), "2_super_novosti")
                db.update_daily_stats(total_messages=1)
                    
            except Exception as e:
                logger.error(f"Ошибка отправки 2 super novosti: {e}")
                # В случае ошибки отправляем базовый текст
                await send_split_message(bot, "😍 2 супер новости", user_id)
            
        elif stage == 2:
            # 2. Что такое онлайн-аватар
            image_path = IMAGES["what_is_avatar"]
            
            if os.path.exists(image_path):
                await send_photo_with_cache(
                    bot, user_id, image_path,
                    caption=TEXTS["what_is_avatar"],
                    reply_markup=get_avatar_info_menu()
                )
            else:
                await send_split_message(
                    bot,
                    TEXTS["what_is_avatar"],
                    user_id,
                    reply_markup=get_avatar_info_menu()
                )
            db.update_daily_stats(total_messages=1)
            
        elif stage == 3:
            # 3. С чем помогает
            image_path = IMAGES["what_helps"]
            
            if os.path.exists(image_path):
                await send_photo_with_cache(
                    bot, user_id, image_path,
                    caption=TEXTS["what_helps"],
                    reply_markup=get_helps_menu()
                )
            else:
                await send_split_message(
                    bot,
                    TEXTS["what_helps"],
                    user_id,
                    reply_markup=get_helps_menu()
                )
            db.update_daily_stats(total_messages=1)
            
        elif stage == 4:
            # 4. Отзывы
            # Отправляем текст отзывов
            await send_split_message(
                bot,
                TEXTS["reviews"],
                user_id,
                reply_markup=get_reviews_menu()
            )
            
            # Отправляем фотографии отзывов с кэшированием
            media_group = []
            total_size = 0
            
            for image_path in REVIEWS_IMAGES:
                if os.path.exists(image_path):
                    try:
                        file_size = os.path.getsize(image_path)
                        max_size = 10 * 1024 * 1024  # 10 МБ
                        
                        if file_size <= max_size:
                            # Проверяем кэш
                            cached_file_id = db.get_media_file_id(image_path)
                            
                            if cached_file_id:
                                media_group.append(InputMediaPhoto(media=cached_file_id))
                                total_size += 100  # Минимальный размер для кэшированного
                            else:
                                photo = FSInputFile(image_path)
                                media_group.append(InputMediaPhoto(media=photo))
                                total_size += file_size
                    except Exception as e:
                        logger.error(f"Ошибка обработки фото отзыва {image_path}: {e}")
            
            if media_group:
                # Разбиваем на группы по 10 фотографий
                chunk_size = 10
                for i in range(0, len(media_group), chunk_size):
                    chunk = media_group[i:i + chunk_size]
                    messages = await bot.send_media_group(user_id, chunk)
                    
                    # Сохраняем file_id для новых фото
                    for j, msg in enumerate(messages):
                        if msg.photo and i + j < len(REVIEWS_IMAGES):
                            img_path = REVIEWS_IMAGES[i + j]
                            if not db.get_media_file_id(img_path):
                                db.save_media_file_id(img_path, msg.photo[-1].file_id, "photo", 
                                                    os.path.getsize(img_path))
                    
                    if i + chunk_size < len(media_group):
                        await asyncio.sleep(0.5)
                
                db.log_traffic("auto_spam_reviews", user_id, "media_group", total_size, "reviews")
                db.update_daily_stats(total_media_sent=len(media_group), total_bytes_sent=total_size)
            
            db.update_daily_stats(total_messages=1)
            
        elif stage == 5:
            # 5. Тарифы - финальное сообщение
            image_path = IMAGES["tariffs"]
            text = TEXTS['tariffs_intro']
            
            if os.path.exists(image_path):
                await send_photo_with_cache(
                    bot, user_id, image_path,
                    caption=text,
                    reply_markup=get_tariffs_menu(user_id)
                )
            else:
                await send_split_message(
                    bot,
                    text,
                    user_id,
                    reply_markup=get_tariffs_menu(user_id)
                )
            
            db.update_daily_stats(total_messages=1)
            
            # Отмечаем в базе данных, что спам завершен
            db.mark_spam_completed(user_id)
            
    except TelegramForbiddenError:
        # Пользователь заблокировал бота
        db.mark_user_blocked(user_id, "Bot blocked during auto spam")
        db.update_daily_stats(blocked_users_count=1)
        logger.debug(f"Пользователь {user_id} заблокировал бота во время автоспама")
    except Exception as e:
        logger.error(f"Ошибка отправки автоспама пользователю {user_id}, этап {stage}: {e}")
        db.log_traffic("auto_spam_error", user_id, "error", 0, None, "error", str(e))

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
                    # Проверяем, не заблокировал ли пользователь бота
                    if db.is_user_blocked(user_id):
                        continue
                    
                    time_diff = current_time - last_activity
                    minutes_since_activity = int(time_diff.total_seconds() // 60)
                    
                    # Проверяем, был ли уже ПОЛНОСТЬЮ завершен/отключен спам в БД
                    if db.is_spam_completed(user_id):
                        continue
                    
                    # Получаем текущий этап спама для пользователя
                    current_stage = user_spam_stage.get(user_id, 0)
                    
                    # Каждый час неактивности = следующий этап (кроме первого - через час)
                    if minutes_since_activity >= 60 and current_stage == 0:
                        needed_stage = 1  # 2 super novosti через час
                    elif minutes_since_activity >= 120 and current_stage <= 1:
                        needed_stage = 2  # что такое аватар через 2 часа
                    elif minutes_since_activity >= 180 and current_stage <= 2:
                        needed_stage = 3  # с чем помогает через 3 часа
                    elif minutes_since_activity >= 240 and current_stage <= 3:
                        needed_stage = 4  # отзывы через 4 часа
                    elif minutes_since_activity >= 300 and current_stage <= 4:
                        needed_stage = 5  # тарифы через 5 часов
                    else:
                        needed_stage = current_stage
                    
                    # Если пользователь неактивен достаточно долго и нужно отправить следующий этап
                    if needed_stage > current_stage and needed_stage <= 5:
                        await send_next_spam_message(bot, user_id, needed_stage)
                        user_spam_stage[user_id] = needed_stage
            
        except Exception as e:
            logger.error(f"Ошибка в автоспам задаче: {e}")
        
        # Проверяем каждые 10 секунд
        await asyncio.sleep(10)