import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from keyboards.inline import get_tariffs_menu, get_tariff_confirm_menu, get_back_to_tariffs
from config import TEXTS, IMAGES, TARIFF_BASIC_PRICE, TARIFF_VIP_PRICE
from promo_utils import get_tariffs_text_with_promo
from auto_spam import update_user_activity

router = Router()

@router.callback_query(F.data == "subscribe")
async def subscribe_handler(callback: CallbackQuery):
    """Выбор тарифа для подписки с промо акцией в одном сообщении"""
    user_id = callback.from_user.id
    update_user_activity(user_id)
    
    image_path = IMAGES["tariffs"]
    
    # НЕ удаляем предыдущее сообщение - отправляем новое
    
    # Получаем текст с промо или без (автоматически)
    text = get_tariffs_text_with_promo()
    
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo,
            caption=text,
            reply_markup=get_tariffs_menu()
        )
    else:
        await callback.message.answer(
            text, 
            reply_markup=get_tariffs_menu()
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
        await callback.message.answer(
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
        await callback.message.answer(
            text, 
            reply_markup=get_tariff_confirm_menu("vip", user_id)
        )
    
    try:
        await callback.answer()
    except Exception:
        pass