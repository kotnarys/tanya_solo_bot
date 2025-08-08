import re
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.config import PERMANENT_ACCESS_IDS, REFERRAL_BONUS
from core.database import db
from services.referral_getcourse import send_referral_data_to_getcourse
from utils.message_utils import answer_split_text

logger = logging.getLogger(__name__)
router = Router()

class ReferralStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_referrer_id = State()

def get_referral_keyboard():
    """Клавиатура для реферальной системы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Реферальная программа", callback_data="referral_main")],
    ])
    return keyboard

def get_referral_main_keyboard(user_id: int):
    """Главная клавиатура реферальной программы"""
    buttons = []
    
    # Проверяем статус регистрации
    if db.is_referral_user_registered(user_id):
        referral_info = db.get_referral_info(user_id)
        
        # Если email не указан - показываем кнопку для указания email
        if not referral_info or not referral_info.get('email'):
            buttons.append([InlineKeyboardButton(text="📧 Указать email", callback_data="referral_register")])
        # Если email указан - пользователь полностью зарегистрирован, кнопок не нужно
    else:
        # Пользователь совсем не зарегистрирован
        buttons.append([InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="referral_register")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def has_referral_access(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя доступ к реферальной программе"""
    from core.database import db
    return db.is_user_subscribed(user_id)

@router.callback_query(F.data == "referral_main")
async def referral_main_menu(callback: CallbackQuery):
    """Главное меню реферальной программы"""
    user_id = callback.from_user.id
    
    # Проверяем доступ
    if not has_referral_access(user_id):
        await callback.answer("❌ Реферальная программа доступна только подписчикам", show_alert=True)
        return
    
    await callback.answer()
    
    # Проверяем, зарегистрирован ли пользователь и указан ли email
    if db.is_referral_user_registered(user_id):
        referral_info = db.get_referral_info(user_id)
        
        # Если email не указан, запрашиваем его
        if not referral_info or not referral_info.get('email'):
            text = """🎁 <b>Реферальная программа</b>

✨ Добро пожаловать в реферальную программу!
💰 За каждого друга получайте <b>500 ₽</b> бонусов

📧 <b>Для активации нужно указать ваш email</b>

⚠️ <b>Важно:</b> Укажите тот же email, который использовали при регистрации на GetCourse платформе"""
            
            await callback.message.answer(text, reply_markup=get_referral_main_keyboard(user_id))
            return
        
        # Пользователь полностью зарегистрирован - показываем полную информацию
        balance = referral_info['referral_balance'] if referral_info else 0
        
        # Получаем реферальную ссылку
        bot_username = "ai_tatyana_solo_bot"
        referral_link = f"https://t.me/{bot_username}?start=r{user_id}"
        
        text = f"""🎁 <b>Реферальная программа</b>

📧 <b>Email:</b> {referral_info['email']}
💰 <b>Ваш баланс:</b> {balance} ₽
✨ <b>Бонус за приглашение:</b> {REFERRAL_BONUS} ₽

🔗 <b>Ваша реферальная ссылка:</b>
<code>{referral_link}</code>

📋 <b>Как это работает:</b>
1. Отправьте ссылку друзьям
2. Они переходят по ссылке и регистрируются
3. При первой оплате вы получаете {REFERRAL_BONUS} ₽

💸 Бонусы автоматически применяются как скидка при оплате подписки

⚠️ <b>Важно для друзей:</b>
• Обязательно нажать команду /start, а не кнопку START
• После регистрации нужно оплатить подписку"""
    else:
        # Пользователь не зарегистрирован вообще
        text = """🎁 <b>Реферальная программа</b>

✨ Приглашайте друзей и получайте бонусы!
💰 За каждого приглашенного друга: <b>500 ₽</b>
💸 Используйте бонусы как скидку на подписку

📝 <b>Для участия необходима регистрация с указанием email</b>"""
    
    await callback.message.answer(text, reply_markup=get_referral_main_keyboard(user_id))

@router.callback_query(F.data == "referral_register")
async def referral_register_start(callback: CallbackQuery, state: FSMContext):
    """Начало регистрации в реферальной системе"""
    user_id = callback.from_user.id
    
    if not has_referral_access(user_id):
        await callback.answer("❌ Реферальная программа доступна только подписчикам", show_alert=True)
        return
    
    await callback.answer()
    
    # Проверяем, есть ли уже email у пользователя
    if db.is_referral_user_registered(user_id):
        referral_info = db.get_referral_info(user_id)
        if referral_info and referral_info.get('email'):
            await callback.message.answer("✅ Вы уже зарегистрированы в реферальной программе!", 
                                            reply_markup=get_referral_main_keyboard(user_id))
            return
    
    text = """📝 <b>Регистрация в реферальной программе</b>

Введите ваш email, который вы указывали при регистрации на GetCourse:

⚠️ <b>Важно:</b> Email должен точно совпадать с тем, что указан в вашем профиле на платформе."""
    
    await callback.message.answer(text)
    await state.set_state(ReferralStates.waiting_for_email)

@router.message(ReferralStates.waiting_for_email)
async def process_email_registration(message: Message, state: FSMContext):
    """Обработка введенного email"""
    user_id = message.from_user.id
    email = message.text.strip()
    
    # Простая валидация email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        await message.answer("❌ Некорректный формат email. Попробуйте еще раз:")
        return
    
    # Проверяем, зарегистрирован ли уже пользователь
    if db.is_referral_user_registered(user_id):
        referral_info = db.get_referral_info(user_id)
        
        # Обновляем email для существующего пользователя
        db.update_referral_user_email(user_id, email)
        
        # Отправляем данные в GetCourse с текущим балансом
        current_balance = referral_info.get('referral_balance', 0) if referral_info else 0
        await send_referral_data_to_getcourse(email, current_balance)
        
        text = f"""✅ <b>Email обновлен!</b>

📧 Email: {email}
💰 Ваш баланс: {current_balance} ₽

🎉 Теперь вы можете полноценно пользоваться реферальной программой!"""
    else:
        # Регистрируем нового пользователя
        db.register_referral_user(user_id, email)
        
        # Отправляем начальные данные в GetCourse
        await send_referral_data_to_getcourse(email, 0)
        
        text = f"""✅ <b>Регистрация завершена!</b>

📧 Email: {email}
💰 Начальный баланс: 0 ₽

🎉 Теперь вы можете получать реферальную ссылку и приглашать друзей!"""
    
    await state.clear()
    await message.answer(text, reply_markup=get_referral_main_keyboard(user_id))


# Функция для добавления реферального бонуса (вызывается из payment handler)
async def add_referral_bonus_if_needed(user_id: int):
    """Добавляет реферальный бонус, если это первая оплата приглашенного пользователя"""
    try:
        logger.info(f"Проверяем начисление реферального бонуса для пользователя {user_id}")
        
        referral_info = db.get_referral_info(user_id)
        if not referral_info or not referral_info['referrer_user_id']:
            logger.info(f"Пользователь {user_id} не был приглашен по реферальной программе")
            return  # Пользователь не был приглашен
        
        referrer_id = referral_info['referrer_user_id']
        logger.info(f"Найден рефер {referrer_id} для пользователя {user_id}")
        
        # Проверяем, не начислялся ли уже бонус за этого пользователя
        conn = db._Database__get_connection() if hasattr(db, '_Database__get_connection') else None
        if not conn:
            import sqlite3
            conn = sqlite3.connect(db.db_path)
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM referral_bonuses 
            WHERE referrer_user_id = ? AND referred_user_id = ?
        ''', (referrer_id, user_id))
        
        if cursor.fetchone():
            conn.close()
            logger.info(f"Бонус уже был начислен реферу {referrer_id} за пользователя {user_id}")
            return  # Бонус уже начислялся
        
        conn.close()
        
        # Начисляем бонус
        logger.info(f"Начисляем бонус {REFERRAL_BONUS} руб. реферу {referrer_id} за пользователя {user_id}")
        if db.add_referral_bonus(referrer_id, user_id, REFERRAL_BONUS):
            logger.info(f"Бонус успешно начислен реферу {referrer_id}")
            
            # Отправляем обновленный баланс в GetCourse
            referrer_info = db.get_referral_info(referrer_id)
            if referrer_info and referrer_info['email']:
                logger.info(f"Отправляем обновленный баланс в GetCourse для {referrer_info['email']}")
                await send_referral_data_to_getcourse(
                    referrer_info['email'], 
                    referrer_info['referral_balance']
                )
            else:
                logger.warning(f"Email не найден для рефера {referrer_id}")
                
        else:
            logger.error(f"Ошибка начисления бонуса реферу {referrer_id}")
            
        logger.info(f"Завершено начисление реферального бонуса для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка начисления реферального бонуса: {e}")