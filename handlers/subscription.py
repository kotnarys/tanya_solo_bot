from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from core.database import db
from datetime import datetime
from utils.message_utils import answer_split_text

router = Router()

@router.message(Command("subscription", "подписка"))
async def check_subscription(message: Message):
    """Проверка статуса подписки пользователя"""
    user_id = message.from_user.id
    
    # Проверяем вечный доступ
    from core.config import PERMANENT_ACCESS_IDS
    if user_id in PERMANENT_ACCESS_IDS:
        text = """✅ <b>У вас вечный доступ!</b>

🌟 <b>Статус:</b> Администратор
♾️ <b>Действует:</b> Бессрочно

🎉 Все функции ИИ Татьяны Соло доступны!"""
        
    else:
        subscription = db.get_user_subscription(user_id)
        
        if subscription and subscription.get('is_active'):
            if subscription['tariff_type'] == 'basic':
                tariff_name = "«Для себя»"  
            elif subscription['tariff_type'] == 'vip':
                tariff_name = "«ВИП Жизнь»"
            elif subscription['tariff_type'] == 'course':
                tariff_name = "«Курс»"
            else:
                tariff_name = "«Неизвестный тариф»"
            expires_date = datetime.fromisoformat(subscription['expires_at']).strftime('%d.%m.%Y')
            days_left = subscription['days_left']
            
            text = f"""✅ <b>У вас активная подписка!</b>

🎯 <b>Тариф:</b> {tariff_name}
📅 <b>Действует до:</b> {expires_date}
⏰ <b>Осталось дней:</b> {days_left}

🎉 Все функции ИИ Татьяны Соло доступны!"""
            
        elif subscription and subscription.get('is_expired'):
            text = """❌ <b>Ваша подписка истекла</b>

💫 Продлите подписку, чтобы продолжить пользоваться всеми возможностями ИИ Татьяны Соло!

🔄 Нажмите "ОФОРМИТЬ ПОДПИСКУ" в главном меню"""
            
        else:
            text = """🤖 <b>У вас пока нет подписки</b>

✨ Оформите подписку, чтобы получить доступ ко всем функциям ИИ Татьяны Соло!

👉 Нажмите "ОФОРМИТЬ ПОДПИСКУ" в главном меню"""
    
    await answer_split_text(message, text)

