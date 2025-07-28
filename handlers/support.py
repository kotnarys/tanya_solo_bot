from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import get_support_menu
from config import SUPPORT_USERNAME

router = Router()

@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery):
    """Обработка запроса в службу заботы"""
    text = f"""🆘 <b>Служба заботы</b>

Если у вас есть вопросы или нужна помощь, наша команда заботы готова вам помочь!

📞 Мы отвечаем в течение 24 часов
💬 Напишите нам: {SUPPORT_USERNAME}

Или нажмите кнопку ниже для быстрого перехода в чат заботы."""
    
    # НЕ удаляем предыдущее сообщение - отправляем новое
    await callback.message.answer(text, reply_markup=get_support_menu())
    
    await callback.answer()