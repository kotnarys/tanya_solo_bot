from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utm_manager import get_payment_url_with_utm

def get_main_menu():
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ОФОРМИТЬ ПОДПИСКУ 🙌🏻", callback_data="subscribe")],
        [InlineKeyboardButton(text="Что такое онлайн-аватар 🤖", callback_data="what_is_avatar")],
        [InlineKeyboardButton(text="Служба заботы 💬", callback_data="support")]
    ])

def get_avatar_info_menu():
    """Меню информации об аватаре"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ХОЧУ ДОСТУП ✨", callback_data="subscribe")],
        [InlineKeyboardButton(text="С чем помогает онлайн-аватар 🫶🏻", callback_data="what_helps")],
        [InlineKeyboardButton(text="← Назад", callback_data="back_to_main")]
    ])

def get_helps_menu():
    """Меню возможностей"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ОФОРМИТЬ ПОДПИСКУ 😍", callback_data="subscribe")],
        [InlineKeyboardButton(text="Отзывы", callback_data="reviews")],
        [InlineKeyboardButton(text="← Назад", callback_data="what_is_avatar")]
    ])

def get_tariffs_menu():
    """Меню выбора тарифа"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌷 «Для себя» - 4 444 руб", callback_data="tariff_basic")],
        [InlineKeyboardButton(text="🌟 «ВИП Жизнь» - 6 666 руб", callback_data="tariff_vip")],
        [InlineKeyboardButton(text="💬 Отзывы", callback_data="reviews")],
        [InlineKeyboardButton(text="← Назад", callback_data="back_to_main")]
    ])

def get_tariff_confirm_menu(tariff_type, user_id=None):
    """Меню подтверждения тарифа с UTM метками пользователя"""
    import time
    
    # Генерируем идентификатор платежа
    if user_id:
        timestamp = int(time.time())
        payment_id = f"bot_{user_id}_{tariff_type}_{timestamp}"
    else:
        payment_id = f"bot_unknown_{tariff_type}_{int(time.time())}"
    
    # Определяем базовую ссылку и текст кнопки
    if tariff_type == "basic":
        button_text = "👉 ОФОРМИТЬ ТАРИФ"
        base_url = "https://solotatiana.getcourse.ru/avatarself"
    else:
        button_text = "👉 ОФОРМИТЬ ВИП"
        base_url = "https://solotatiana.getcourse.ru/avatarvip"
    
    # Строим ссылку с UTM метками пользователя
    if user_id:
        url = get_payment_url_with_utm(user_id, base_url, payment_id)
    else:
        # Fallback для случаев без user_id
        url = f"{base_url}?id={payment_id}&utm_source=telegram_bot&utm_medium=button&utm_campaign=avatarai"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, url=url)],
        [InlineKeyboardButton(text="← К выбору тарифа", callback_data="subscribe")]
    ])

def get_back_to_tariffs():
    """Кнопка назад к тарифам"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← К выбору тарифа", callback_data="subscribe")]
    ])

def get_reviews_menu():
    """Меню отзывов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ОФОРМИТЬ ПОДПИСКУ 😍", callback_data="subscribe")],
        [InlineKeyboardButton(text="← Назад к тарифам", callback_data="subscribe")]
    ])

def get_support_menu():
    """Меню поддержки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать в службу заботы", url="https://t.me/zabotasolo")],
        [InlineKeyboardButton(text="← Назад", callback_data="back_to_main")]
    ])

def get_documents_menu():
    """Меню с документами после оплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Политика конфиденциальности", url="https://solotatiana.getcourse.ru/privacysolo")],
        [InlineKeyboardButton(text="📄 Согласие на рекламные материалы", url="https://solotatiana.getcourse.ru/agreement")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])