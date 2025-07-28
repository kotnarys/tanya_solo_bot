import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from keyboards.inline import get_main_menu
from config import TEXTS, IMAGES, VIDEOS
from utm_manager import parse_and_save_utm, is_video_already_sent, mark_video_as_sent
from auto_spam import update_user_activity, update_user_activity_start_only

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
    
    # Сначала отправляем основное сообщение с картинкой и кнопками
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await message.answer_photo(
            photo, 
            caption=TEXTS["main"], 
            reply_markup=get_main_menu()
        )
    else:
        # Если изображения нет, отправляем только текст
        await message.answer(TEXTS["main"], reply_markup=get_main_menu())
    
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
                    print(f"Видео {path} слишком большое: {file_size / 1024 / 1024:.1f} МБ (максимум 50 МБ)")
        
        if video_path:
            try:
                video = FSInputFile(video_path)
                # Отправляем как видеокружок (video note) вместо обычного видео
                await message.answer_video_note(video, request_timeout=120)
                mark_video_as_sent(user_id)
                print(f"Видеокружок отправлен пользователю {user_id} при первом /start")
            except Exception as e:
                print(f"Ошибка отправки видеокружка: {e}")
    else:
        print(f"Видео уже отправлялось пользователю {user_id}, пропускаем")

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
            reply_markup=get_main_menu()
        )
    else:
        # Если изображения нет, отправляем только текст
        await callback.message.answer(TEXTS["main"], reply_markup=get_main_menu())