from aiogram import Router, F
from aiogram.types import Message, Voice, Audio
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import os
import tempfile

from core.openai_client import openai_client
from core.database import db
from utils.message_utils import answer_split_text

logger = logging.getLogger(__name__)

router = Router()

class AIChat(StatesGroup):
    waiting_for_message = State()

@router.message(F.text)
async def handle_ai_chat(message: Message, state: FSMContext):
    """Обработчик всех текстовых сообщений для OpenAI чата (для подписчиков с 30 июля 15:00 МСК)"""
    
    try:
        user_id = message.from_user.id
        text = message.text
        
        # Проверяем, есть ли у пользователя доступ к OpenAI
        has_access = openai_client.has_openai_access(user_id)
        
        if not has_access:
            # Отправляем сообщение о необходимости подписки
            await message.answer("💎 Привет, дорогая! Для общения со мной нужна активная подписка.\n\n🌟 Выбери подходящий тариф и получи доступ ко всем функциям ИИ Татьяны Соло!\n\n👉 Жми /start чтобы посмотреть тарифы")
            return
        
        # Используем общую функцию для обработки текста
        await process_text_message(message, user_id, text)
        
    except Exception as e:
        logger.error(f"❌ AI handler error for user {message.from_user.id}: {e}")
        try:
            await message.answer("😔 Произошла техническая ошибка. Попробуй еще раз через минутку 💕")
        except:
            pass

@router.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext):
    """Обработчик голосовых сообщений"""
    
    user_id = message.from_user.id
    
    # Проверяем, есть ли у пользователя доступ к OpenAI
    if not openai_client.has_openai_access(user_id):
        return  # Игнорируем сообщения от пользователей без доступа
    
    try:
        # Отправляем индикатор печати (с обработкой flood control)
        try:
            await message.bot.send_chat_action(message.chat.id, "typing")
        except Exception:
            pass  # Игнорируем ошибки flood control
        
        # Скачиваем голосовое сообщение
        voice_file = await message.bot.get_file(message.voice.file_id)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            temp_path = temp_file.name
            await message.bot.download_file(voice_file.file_path, temp_path)
        
        # Расшифровываем аудио в текст
        transcribed_text = await openai_client.transcribe_audio(user_id, temp_path)
        
        # Удаляем временный файл
        os.unlink(temp_path)
        
        if not transcribed_text:
            await answer_split_text(message, "❌ Не удалось распознать голосовое сообщение. Попробуйте еще раз.")
            return
        
        # Сразу обрабатываем как обычное текстовое сообщение (без показа распознанного текста)
        await process_text_message(message, user_id, transcribed_text)
        
    except Exception as e:
        logger.error(f"Ошибка обработки голосового сообщения для пользователя {user_id}: {e}")
        await answer_split_text(message, "❌ Ошибка обработки голосового сообщения. Попробуйте еще раз.")

@router.message(F.audio)
async def handle_audio_message(message: Message, state: FSMContext):
    """Обработчик аудио файлов"""
    
    user_id = message.from_user.id
    
    # Проверяем, есть ли у пользователя доступ к OpenAI
    if not openai_client.has_openai_access(user_id):
        return  # Игнорируем сообщения от пользователей без доступа
    
    try:
        # Отправляем индикатор печати (с обработкой flood control)
        try:
            await message.bot.send_chat_action(message.chat.id, "typing")
        except Exception:
            pass  # Игнорируем ошибки flood control
        
        # Скачиваем аудио файл
        audio_file = await message.bot.get_file(message.audio.file_id)
        
        # Создаем временный файл с правильным расширением
        file_extension = ".mp3" if message.audio.mime_type == "audio/mpeg" else ".ogg"
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_path = temp_file.name
            await message.bot.download_file(audio_file.file_path, temp_path)
        
        # Расшифровываем аудио в текст
        transcribed_text = await openai_client.transcribe_audio(user_id, temp_path)
        
        # Удаляем временный файл
        os.unlink(temp_path)
        
        if not transcribed_text:
            await answer_split_text(message, "❌ Не удалось распознать аудио файл. Попробуйте еще раз.")
            return
        
        # Сразу обрабатываем как обычное текстовое сообщение (без показа распознанного текста)
        await process_text_message(message, user_id, transcribed_text)
        
    except Exception as e:
        logger.error(f"Ошибка обработки аудио файла для пользователя {user_id}: {e}")
        await answer_split_text(message, "❌ Ошибка обработки аудио файла. Попробуйте еще раз.")

@router.message(F.photo)
async def handle_photo_message(message: Message, state: FSMContext):
    """Обработчик фотографий"""
    
    user_id = message.from_user.id
    
    # Проверяем, есть ли у пользователя доступ к OpenAI
    if not openai_client.has_openai_access(user_id):
        return  # Игнорируем сообщения от пользователей без доступа
    
    # Ласковое сообщение о том, что изображения не поддерживаются
    await answer_split_text(message, "🤗 Милая, я пока не умею работать с изображениями, но очень хочу этому научиться! ✨\n\nМожешь описать мне словами, что на фото? Я с удовольствием помогу тебе с любым вопросом в текстовом формате 💕")

async def process_text_message(message: Message, user_id: int, text: str):
    """Общая функция для обработки текстовых сообщений (из текста или расшифрованных аудио)"""
    
    try:
        # Проверяем, есть ли уже thread для пользователя
        thread_info = db.get_openai_thread(user_id)
        
        if not thread_info:
            # Создаем новый thread
            thread_id = await openai_client.create_thread(user_id)
            if not thread_id:
                await answer_split_text(message, "❌ Ошибка создания сессии чата")
                return
            
            # Сохраняем thread в БД
            db.save_openai_thread(user_id, thread_id)
        else:
            thread_id = thread_info['thread_id']
        
        # Отправляем индикатор печати (с обработкой flood control)
        try:
            await message.bot.send_chat_action(message.chat.id, "typing")
        except Exception:
            pass  # Игнорируем ошибки flood control
        
        # Получаем ответ от OpenAI через Assistant API
        response = await openai_client.send_message(user_id, thread_id, text)
        
        if response:
            # Очищаем HTML теги, которые может вернуть OpenAI
            clean_response = response.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
            # Удаляем другие HTML теги
            import re
            clean_response = re.sub(r'<[^>]+>', '', clean_response)
            await answer_split_text(message, clean_response)
        else:
            logger.error(f"❌ No AI response for user {user_id}")
            await answer_split_text(message, "😔 Что-то пошло не так... Попробуй написать еще раз или переформулировать вопрос 💕\n\nЕсли проблема повторяется, напиши /start и попробуй снова.")
        
    except Exception as e:
        # Игнорируем flood control ошибки для send_chat_action
        if "Flood control exceeded" in str(e) and "SendChatAction" in str(e):
            logger.warning(f"⚠️ Flood control для пользователя {user_id}, продолжаем без typing индикатора")
            return
        
        logger.error(f"❌ Error in process_text_message for {user_id}: {e}")
        try:
            await message.answer("😔 Произошла ошибка при обработке сообщения 💕")
        except:
            pass

