import asyncio
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.config import NEWS_ADMIN_IDS
from core.database import db
from utils.message_utils import answer_split_text

logger = logging.getLogger(__name__)
router = Router()

class NewsStates(StatesGroup):
    choosing_audience = State()      # Выбор аудитории
    waiting_for_message = State()    # Ожидание сообщения
    confirming_send = State()        # Подтверждение отправки

def get_audience_menu():
    """Меню выбора аудитории для рассылки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Всем пользователям бота", callback_data="news_all_users")],
        [InlineKeyboardButton(text="✅ Только активным подписчикам", callback_data="news_active_subscribers")],
        [InlineKeyboardButton(text="🎓 Только участникам курса", callback_data="news_course_users")],
        [InlineKeyboardButton(text="💎 Только платным подписчикам", callback_data="news_paid_subscribers")],
        [InlineKeyboardButton(text="🌟 Только VIP пользователям", callback_data="news_vip_users")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="news_cancel")]
    ])
    return keyboard

def get_confirmation_menu():
    """Меню подтверждения отправки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="news_confirm_send")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="news_cancel")]
    ])
    return keyboard

@router.message(Command("news"))
async def news_command(message: Message, state: FSMContext):
    """Команда /news для админов"""
    user_id = message.from_user.id
    
    # Проверяем права админа
    if user_id not in NEWS_ADMIN_IDS:
        await message.answer("❌ У вас нет прав доступа к этой функции")
        return
    
    text = """🔧 <b>Админ панель - Рассылка новостей</b>

Выберите аудиторию для рассылки:"""
    
    await message.answer(text, reply_markup=get_audience_menu())
    await state.set_state(NewsStates.choosing_audience)

@router.callback_query(F.data.startswith("news_"))
async def handle_news_callbacks(callback: CallbackQuery, state: FSMContext):
    """Обработка всех callback'ов для рассылки новостей"""
    user_id = callback.from_user.id
    
    # Проверяем права админа
    if user_id not in NEWS_ADMIN_IDS:
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    data = callback.data
    
    if data == "news_cancel":
        await callback.message.edit_text("❌ Рассылка отменена")
        await state.clear()
        await callback.answer()
        return
    
    # Выбор аудитории
    if data in ["news_all_users", "news_active_subscribers", "news_course_users", "news_paid_subscribers", "news_vip_users"]:
        audience_names = {
            "news_all_users": "📢 Всем пользователям бота",
            "news_active_subscribers": "✅ Только активным подписчикам", 
            "news_course_users": "🎓 Только участникам курса",
            "news_paid_subscribers": "💎 Только платным подписчикам",
            "news_vip_users": "🌟 Только VIP пользователям"
        }
        
        audience_type = data.replace("news_", "")
        audience_name = audience_names[data]
        
        # Сохраняем выбор в состоянии
        await state.update_data(audience_type=audience_type, audience_name=audience_name)
        
        await callback.message.edit_text(
            f"📝 <b>Напишите сообщение для рассылки:</b>\n\n"
            f"Аудитория: {audience_name}\n\n"
            f"⚠️ Поддерживаются: текст, фото, видео, документы, голосовые сообщения\n\n"
            f"💡 Чтобы отменить рассылку, напишите: <b>ОТМЕНА</b>"
        )
        await state.set_state(NewsStates.waiting_for_message)
        await callback.answer()
        return
    
    # Подтверждение отправки
    if data == "news_confirm_send":
        await callback.answer("🚀 Начинаю рассылку...")
        
        # Получаем данные из состояния
        user_data = await state.get_data()
        audience_type = user_data.get("audience_type")
        message_data = user_data.get("message_data")
        
        if not audience_type or not message_data:
            await callback.message.edit_text("❌ Ошибка: данные для рассылки не найдены")
            await state.clear()
            return
        
        # Запускаем рассылку
        await start_broadcast(callback.message, audience_type, message_data, user_id, state)
        return

@router.message(NewsStates.waiting_for_message)
async def handle_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки от админа"""
    user_id = message.from_user.id
    
    # Проверяем права админа
    if user_id not in NEWS_ADMIN_IDS:
        await message.answer("❌ У вас нет прав доступа")
        await state.clear()
        return
    
    # Проверяем команду отмены
    if message.text and message.text.upper().strip() == "ОТМЕНА":
        await message.answer("❌ Рассылка отменена")
        await state.clear()
        return
    
    # Получаем данные о выбранной аудитории
    user_data = await state.get_data()
    audience_type = user_data.get("audience_type")
    audience_name = user_data.get("audience_name")
    
    if not audience_type:
        await message.answer("❌ Ошибка: аудитория не выбрана")
        await state.clear()
        return
    
    # Сохраняем данные сообщения
    message_data = {
        "text": message.text,
        "content_type": message.content_type,
        "message_id": message.message_id
    }
    
    # Обрабатываем разные типы контента
    if message.photo:
        message_data["photo"] = message.photo[-1].file_id
        message_data["caption"] = message.caption
    elif message.video:
        message_data["video"] = message.video.file_id
        message_data["caption"] = message.caption
    elif message.document:
        message_data["document"] = message.document.file_id
        message_data["caption"] = message.caption
    elif message.voice:
        message_data["voice"] = message.voice.file_id
    elif message.video_note:
        message_data["video_note"] = message.video_note.file_id
    
    # Сохраняем данные сообщения в состоянии
    await state.update_data(message_data=message_data)
    
    # Показываем превью и запрашиваем подтверждение
    preview_text = f"""📋 <b>Предварительный просмотр рассылки:</b>

<b>Аудитория:</b> {audience_name}

<b>Содержимое:</b> {get_content_description(message)}

Отправить рассылку?"""
    
    await message.answer(preview_text, reply_markup=get_confirmation_menu())
    await state.set_state(NewsStates.confirming_send)

async def start_broadcast(message: Message, audience_type: str, message_data: dict, admin_id: int, state: FSMContext):
    """Запуск массовой рассылки"""
    try:
        # Получаем список получателей
        recipients = get_recipients_list(audience_type)
        
        if not recipients:
            await message.edit_text("❌ Не найдено получателей для выбранной аудитории")
            await state.clear()
            return
        
        # Создаем запись в БД о рассылке
        broadcast_id = db.create_news_broadcast(
            admin_id=admin_id,
            audience_type=audience_type,
            message_text=message_data.get("text", ""),
            media_type=message_data.get("content_type", "text"),
            total_recipients=len(recipients)
        )
        
        # Показываем прогресс
        progress_message = await message.edit_text(
            f"🚀 <b>Рассылка запущена</b>\n\n"
            f"📤 Отправлено: 0\n"
            f"❌ Ошибок: 0"
        )
        
        # Запускаем рассылку
        sent_count, error_count = await send_broadcast_messages(recipients, message_data, progress_message)
        
        # Обновляем статистику в БД
        db.update_news_broadcast_stats(broadcast_id, sent_count, error_count)
        
        # Показываем итоговый результат
        await progress_message.edit_text(
            f"✅ <b>Рассылка завершена</b>\n\n"
            f"📤 Успешно отправлено: {sent_count}\n"
            f"❌ Ошибок: {error_count}"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка рассылки: {e}")
        await message.edit_text(f"❌ Ошибка при рассылке: {str(e)}")
        await state.clear()

async def send_broadcast_messages(recipients: list, message_data: dict, progress_message: Message):
    """Отправка сообщений получателям с обновлением прогресса"""
    sent_count = 0
    error_count = 0
    
    for i, user_id in enumerate(recipients):
        try:
            # Отправляем сообщение в зависимости от типа контента
            bot = progress_message.bot
            
            if message_data.get("photo"):
                await bot.send_photo(
                    user_id, 
                    message_data["photo"], 
                    caption=message_data.get("caption")
                )
            elif message_data.get("video"):
                await bot.send_video(
                    user_id, 
                    message_data["video"], 
                    caption=message_data.get("caption")
                )
            elif message_data.get("document"):
                await bot.send_document(
                    user_id, 
                    message_data["document"], 
                    caption=message_data.get("caption")
                )
            elif message_data.get("voice"):
                await bot.send_voice(user_id, message_data["voice"])
            elif message_data.get("video_note"):
                await bot.send_video_note(user_id, message_data["video_note"])
            else:
                await bot.send_message(user_id, message_data.get("text", ""))
            
            sent_count += 1
            
        except Exception as e:
            error_count += 1
            logger.warning(f"Ошибка отправки пользователю {user_id}: {e}")
        
        # Обновляем прогресс каждые 10 сообщений
        if (i + 1) % 10 == 0:
            try:
                await progress_message.edit_text(
                    f"🚀 <b>Рассылка в процессе</b>\n\n"
                    f"📤 Отправлено: {sent_count}\n"
                    f"❌ Ошибок: {error_count}"
                )
            except:
                pass  # Игнорируем ошибки обновления прогресса
        
        # Небольшая пауза для избежания flood control
        await asyncio.sleep(0.05)
    
    return sent_count, error_count

def get_recipients_count(audience_type: str) -> int:
    """Получает количество получателей для выбранной аудитории"""
    if audience_type == "all_users":
        return db.get_all_users_count()
    elif audience_type == "active_subscribers":
        return len(db.get_active_subscribers())
    elif audience_type == "course_users":
        return db.get_course_users_count()
    elif audience_type == "paid_subscribers":
        return db.get_paid_subscribers_count()
    elif audience_type == "vip_users":
        return db.get_vip_users_count()
    else:
        return 0

def get_recipients_list(audience_type: str) -> list:
    """Получает список получателей для выбранной аудитории"""
    if audience_type == "all_users":
        return db.get_all_users()
    elif audience_type == "active_subscribers":
        return db.get_active_subscribers()
    elif audience_type == "course_users":
        return db.get_course_users()
    elif audience_type == "paid_subscribers":
        return db.get_paid_subscribers()
    elif audience_type == "vip_users":
        return db.get_vip_users()
    else:
        return []

def get_content_description(message: Message) -> str:
    """Получает описание типа контента сообщения"""
    if message.photo:
        return f"Фото{' с подписью' if message.caption else ''}"
    elif message.video:
        return f"Видео{' с подписью' if message.caption else ''}"
    elif message.document:
        return f"Документ{' с подписью' if message.caption else ''}"
    elif message.voice:
        return "Голосовое сообщение"
    elif message.video_note:
        return "Видеосообщение"
    else:
        return "Текстовое сообщение"