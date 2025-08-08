import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from keyboards.inline import get_tariffs_menu, get_tariff_confirm_menu, get_back_to_tariffs
from core.config import TEXTS, IMAGES, TARIFF_BASIC_PRICE, TARIFF_VIP_PRICE, PERMANENT_ACCESS_IDS
# from promo_utils import get_tariffs_text_with_promo  # Удален файл promo_utils.py
from background.auto_spam import update_user_activity
from utils.message_utils import answer_split_text
from core.database import db

router = Router()

def get_price_with_referral_discount(user_id: int, original_price: int):
    """
    Вычисляет цену с учетом реферального баланса
    
    Args:
        user_id: ID пользователя
        original_price: Оригинальная цена
        
    Returns:
        tuple: (discounted_price, discount_amount, has_discount)
    """
    # Проверяем, есть ли у пользователя доступ к реферальной программе
    if user_id not in PERMANENT_ACCESS_IDS:
        return original_price, 0, False
    
    # Проверяем, есть ли у пользователя реферальный баланс
    if not db.is_referral_user_registered(user_id):
        return original_price, 0, False
    
    referral_info = db.get_referral_info(user_id)
    if not referral_info:
        return original_price, 0, False
    
    referral_balance = referral_info['referral_balance']
    if referral_balance <= 0:
        return original_price, 0, False
    
    # Вычисляем скидку (не больше цены товара)
    discount = min(referral_balance, original_price)
    discounted_price = max(0, original_price - discount)
    
    return discounted_price, discount, True

def format_price_with_discount(original_price: int, discounted_price: int, discount: int, has_discount: bool):
    """Форматирует цену со скидкой"""
    if not has_discount or discount == 0:
        return f"{original_price:,} ₽".replace(",", " ")
    
    if discounted_price == 0:
        return f"~~{original_price:,} ₽~~ **БЕСПЛАТНО** 🎉".replace(",", " ")
    
    return f"~~{original_price:,} ₽~~ **{discounted_price:,} ₽** (-{discount} ₽)".replace(",", " ")

@router.callback_query(F.data == "subscribe")
async def subscribe_handler(callback: CallbackQuery):
    """Выбор тарифа для подписки с промо акцией в одном сообщении"""
    user_id = callback.from_user.id
    update_user_activity(user_id)
    
    image_path = IMAGES["tariffs"]
    
    # НЕ удаляем предыдущее сообщение - отправляем новое
    
    # Получаем текст с промо или без (автоматически)
    text = TEXTS['tariffs_intro']
    
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo,
            caption=text,
            reply_markup=get_tariffs_menu(user_id)
        )
    else:
        await answer_split_text(
            callback.message,
            text, 
            reply_markup=get_tariffs_menu(user_id)
        )
    
    try:
        await callback.answer()
    except Exception:
        pass

@router.callback_query(F.data == "tariff_basic")
async def tariff_basic_handler(callback: CallbackQuery):
    """Показ базового тарифа"""
    user_id = callback.from_user.id
    update_user_activity(user_id)
    
    text = TEXTS['tariff_basic']
    image_path = IMAGES["tariffs"]
    
    # НЕ удаляем предыдущее сообщение - отправляем новое
    
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo,
            caption=text,
            reply_markup=get_tariff_confirm_menu("basic", user_id)
        )
    else:
        await answer_split_text(
            callback.message,
            text, 
            reply_markup=get_tariff_confirm_menu("basic", user_id)
        )
    
    try:
        await callback.answer()
    except Exception:
        pass

@router.callback_query(F.data == "tariff_vip")
async def tariff_vip_handler(callback: CallbackQuery):
    """Показ VIP тарифа"""
    user_id = callback.from_user.id
    update_user_activity(user_id)
    
    text = TEXTS['tariff_vip']
    image_path = IMAGES["tariffs"]
    
    # НЕ удаляем предыдущее сообщение - отправляем новое
    
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo,
            caption=text,
            reply_markup=get_tariff_confirm_menu("vip", user_id)
        )
    else:
        await answer_split_text(
            callback.message,
            text, 
            reply_markup=get_tariff_confirm_menu("vip", user_id)
        )
    
    try:
        await callback.answer()
    except Exception:
        pass