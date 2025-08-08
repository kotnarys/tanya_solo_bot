import os
import asyncio
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from keyboards.inline import get_avatar_info_menu, get_helps_menu, get_reviews_menu
from core.config import TEXTS, IMAGES, REVIEWS_IMAGES
from background.auto_spam import update_user_activity
from utils.message_utils import answer_split_text

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data == "what_is_avatar")
async def what_is_avatar_handler(callback: CallbackQuery):
    """Информация о том, что такое онлайн-аватар"""
    user_id = callback.from_user.id
    update_user_activity(user_id)
    
    image_path = IMAGES["what_is_avatar"]
    
    # НЕ удаляем предыдущее сообщение - отправляем новое
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo,
            caption=TEXTS["what_is_avatar"],
            reply_markup=get_avatar_info_menu()
        )
    else:
        await answer_split_text(
            callback.message,
            TEXTS["what_is_avatar"], 
            reply_markup=get_avatar_info_menu()
        )
    
    try:
        await callback.answer()
    except Exception:
        pass

@router.callback_query(F.data == "what_helps")
async def what_helps_handler(callback: CallbackQuery):
    """Информация о возможностях аватара"""
    user_id = callback.from_user.id
    update_user_activity(user_id)
    
    image_path = IMAGES["what_helps"]
    
    # НЕ удаляем предыдущее сообщение - отправляем новое
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo,
            caption=TEXTS["what_helps"],
            reply_markup=get_helps_menu()
        )
    else:
        await answer_split_text(
            callback.message,
            TEXTS["what_helps"], 
            reply_markup=get_helps_menu()
        )
    
    try:
        await callback.answer()
    except Exception:
        pass

@router.callback_query(F.data == "reviews")
async def reviews_handler(callback: CallbackQuery):
    """Отзывы пользователей"""
    user_id = callback.from_user.id
    update_user_activity(user_id)
    
    # НЕ удаляем предыдущее сообщение - отправляем новое
    
    # Сначала отправляем основной текст с кнопками
    await answer_split_text(
        callback.message,
        TEXTS["reviews"], 
        reply_markup=get_reviews_menu()
    )
    
    # Собираем фотографии отзывов
    media_group = []
    
    for image_path in REVIEWS_IMAGES:
        if os.path.exists(image_path):
            try:
                # Проверяем размер файла (максимум 10 МБ для фото в Telegram)
                file_size = os.path.getsize(image_path)
                max_size = 10 * 1024 * 1024  # 10 МБ
                
                if file_size <= max_size:
                    photo = FSInputFile(image_path)
                    media_group.append(InputMediaPhoto(media=photo))
            except Exception as e:
                logger.error(f"Ошибка при обработке файла {image_path}: {e}")
    
    # Отправляем медиагруппу с фотографиями отзывов
    if media_group:
        try:
            # Отправляем все фото одной группой (максимум 10 фото в Telegram)
            await callback.message.answer_media_group(media_group)
        except Exception as e:
            logger.error(f"Ошибка отправки медиагруппы отзывов: {e}")
            await answer_split_text(callback.message, "📸 Ошибка загрузки фотографий отзывов. Попробуйте позже.")
    
    try:
        await callback.answer()
    except Exception:
        pass