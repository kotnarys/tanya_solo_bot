import os
import logging
import sqlite3
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from keyboards.inline import get_main_menu
from core.config import TEXTS, IMAGES, VIDEOS
from services.utm_manager import parse_and_save_utm, is_video_already_sent, mark_video_as_sent
from background.auto_spam import update_user_activity, update_user_activity_start_only
from utils.message_utils import answer_split_text
from core.database import db

logger = logging.getLogger(__name__)

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    """Стартовое сообщение с обработкой UTM меток"""
    video_paths = VIDEOS["main"]
    image_path = IMAGES["main"]
    user_id = message.from_user.id
    
    # Обновляем активность ТОЛЬКО для /start (не отключаем автоспам)
    update_user_activity_start_only(user_id)
    
    # Получаем параметр start из команды
    start_param = None
    if message.text and len(message.text.split()) > 1:
        start_param = message.text.split(maxsplit=1)[1]
    
    # Парсим и сохраняем UTM метки, если есть
    if start_param:
        parse_and_save_utm(user_id, start_param)
        
        # Обработка реферальных ссылок (формат: r123456789)
        if start_param.startswith('r') and start_param[1:].isdigit():
            referrer_id = int(start_param[1:])
            await process_referral_link(user_id, referrer_id)
    
    # Сначала отправляем основное сообщение с картинкой и кнопками
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await message.answer_photo(
            photo, 
            caption=TEXTS["main"], 
            reply_markup=get_main_menu(user_id)
        )
    else:
        # Если изображения нет, отправляем только текст
        await answer_split_text(message, TEXTS["main"], reply_markup=get_main_menu(user_id))
    
    # Затем отправляем видеокружок отдельно (если есть) ТОЛЬКО при первом /start
    if not is_video_already_sent(user_id):
        video_path = None
        for path in video_paths:
            if os.path.exists(path):
                # Проверяем размер файла (50 МБ = 50 * 1024 * 1024 байт)
                file_size = os.path.getsize(path)
                max_size = 50 * 1024 * 1024  # 50 МБ
                
                if file_size <= max_size:
                    video_path = path
                    break
                else:
                    logger.warning(f"Видео {path} слишком большое: {file_size / 1024 / 1024:.1f} МБ (максимум 50 МБ)")
        
        if video_path:
            try:
                video = FSInputFile(video_path)
                # Отправляем как видеокружок (video note) вместо обычного видео
                await message.answer_video_note(video, request_timeout=120)
                mark_video_as_sent(user_id)
                logger.info(f"Видеокружок отправлен пользователю {user_id} при первом /start")
            except Exception as e:
                # Если у пользователя отключены голосовые/видео сообщения, отправляем как обычное видео
                if "VOICE_MESSAGES_FORBIDDEN" in str(e):
                    try:
                        video = FSInputFile(video_path)
                        await message.answer_video(video, request_timeout=120)
                        mark_video_as_sent(user_id)
                        logger.info(f"Видео отправлено как обычное видео пользователю {user_id} (видеокружки запрещены)")
                    except Exception as e2:
                        logger.error(f"Ошибка отправки обычного видео: {e2}")
                else:
                    logger.error(f"Ошибка отправки видеокружка: {e}")
    else:
        logger.debug(f"Видео уже отправлялось пользователю {user_id}, пропускаем")

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат к главному меню - ОТКЛЮЧАЕТ автоспам навсегда"""
    image_path = IMAGES["main"]
    user_id = callback.from_user.id
    
    # Обновляем активность пользователя (ОТКЛЮЧАЕТ автоспам навсегда)
    update_user_activity(user_id)
    
    # Сразу отвечаем на callback с обработкой ошибок
    try:
        await callback.answer()
    except Exception:
        pass
    
    # НЕ удаляем предыдущее сообщение - просто отправляем новое
    # НЕ отправляем видео - только главное меню
    
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo, 
            caption=TEXTS["main"], 
            reply_markup=get_main_menu(user_id)
        )
    else:
        # Если изображения нет, отправляем только текст
        await answer_split_text(callback.message, TEXTS["main"], reply_markup=get_main_menu(user_id))


async def process_referral_link(user_id: int, referrer_id: int):
    """Обрабатывает переход по реферальной ссылке"""
    try:
        # Проверяем, что пользователь не пытается пригласить сам себя
        if user_id == referrer_id:
            logger.warning(f"Пользователь {user_id} пытается использовать свою же реферальную ссылку")
            return
        
        # Проверяем, что реферер существует и зарегистрирован в реферальной системе
        if not db.is_referral_user_registered(referrer_id):
            logger.warning(f"Реферер {referrer_id} не зарегистрирован в реферальной системе")
            return
        
        # Проверяем, не зарегистрирован ли уже пользователь с другим реферером
        if db.is_referral_user_registered(user_id):
            current_referral_info = db.get_referral_info(user_id)
            if current_referral_info and current_referral_info['referrer_user_id']:
                logger.info(f"Пользователь {user_id} уже имеет реферера {current_referral_info['referrer_user_id']}")
                return
        
        # Временно сохраняем информацию о реферере для пользователя
        # Полная регистрация произойдет, когда пользователь введет свой email
        if not db.is_referral_user_registered(user_id):
            # Создаем временную запись без email
            db.register_referral_user(user_id, "", referrer_id)
        else:
            # Обновляем существующую запись
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE referral_users 
                SET referrer_user_id = ?
                WHERE user_id = ? AND referrer_user_id IS NULL
            ''', (referrer_id, user_id))
            conn.commit()
            conn.close()
        
        logger.info(f"Обработан переход по реферальной ссылке: пользователь {user_id} приглашен {referrer_id}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки реферальной ссылки: {e}")