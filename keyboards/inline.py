from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.utm_manager import get_payment_url_with_utm

def get_main_menu(user_id=None):
    """Главное меню"""
    # Базовые кнопки
    buttons = [
        [InlineKeyboardButton(text="ОФОРМИТЬ ПОДПИСКУ 🙌🏻", callback_data="subscribe")],
        [InlineKeyboardButton(text="Что такое онлайн-аватар 🤖", callback_data="what_is_avatar")],
    ]
    
    # Добавляем кнопку реферальной программы для всех пользователей с активной подпиской
    if user_id:
        from core.database import db
        if db.is_user_subscribed(user_id):
            buttons.append([InlineKeyboardButton(text="🎁 Реферальная программа", callback_data="referral_main")])
    
    # Последний ряд кнопок
    buttons.append([
        InlineKeyboardButton(text="Отдел заботы 💬", url="https://t.me/zabotasolo"),
        InlineKeyboardButton(text="Отменить подписку ❌", url="https://solotatiana.getcourse.ru/user/my/profile")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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

def get_tariffs_menu(user_id=None):
    """Меню выбора тарифа"""
    # Базовые цены
    basic_price = 5555
    vip_price = 7777
    
    # Если передан user_id, проверяем реферальный баланс
    if user_id:
        from core.database import db
        
        if db.is_user_subscribed(user_id) and db.is_referral_user_registered(user_id):
            referral_info = db.get_referral_info(user_id)
            if referral_info and referral_info['referral_balance'] > 0:
                balance = referral_info['referral_balance']
                
                # Вычисляем цены со скидкой
                basic_discount = min(balance, basic_price)
                vip_discount = min(balance, vip_price)
                
                basic_final = max(0, basic_price - basic_discount)
                vip_final = max(0, vip_price - vip_discount)
                
                # Форматируем текст кнопок с учетом скидки
                if basic_final == 0:
                    basic_text = "🌷 «Для себя» - БЕСПЛАТНО 🎉"
                elif basic_discount > 0:
                    basic_text = f"🌷 «Для себя» - {basic_final:,} ₽ (-{basic_discount} ₽)".replace(",", " ")
                else:
                    basic_text = f"🌷 «Для себя» - {basic_price:,} руб".replace(",", " ")
                
                if vip_final == 0:
                    vip_text = "🌟 «ВИП Жизнь» - БЕСПЛАТНО 🎉"
                elif vip_discount > 0:
                    vip_text = f"🌟 «ВИП Жизнь» - {vip_final:,} ₽ (-{vip_discount} ₽)".replace(",", " ")
                else:
                    vip_text = f"🌟 «ВИП Жизнь» - {vip_price:,} руб".replace(",", " ")
            else:
                basic_text = f"🌷 «Для себя» - {basic_price:,} руб".replace(",", " ")
                vip_text = f"🌟 «ВИП Жизнь» - {vip_price:,} руб".replace(",", " ")
        else:
            basic_text = f"🌷 «Для себя» - {basic_price:,} руб".replace(",", " ")
            vip_text = f"🌟 «ВИП Жизнь» - {vip_price:,} руб".replace(",", " ")
    else:
        basic_text = f"🌷 «Для себя» - {basic_price:,} руб".replace(",", " ")
        vip_text = f"🌟 «ВИП Жизнь» - {vip_price:,} руб".replace(",", " ")
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=basic_text, callback_data="tariff_basic")],
        [InlineKeyboardButton(text=vip_text, callback_data="tariff_vip")],
        [InlineKeyboardButton(text="💬 Отзывы", callback_data="reviews")],
        [InlineKeyboardButton(text="← Назад", callback_data="back_to_main")]
    ])

def get_tariff_confirm_menu(tariff_type, user_id=None):
    """Меню подтверждения тарифа с UTM метками пользователя"""
    import time
    
    # Получаем реферальный баланс пользователя для включения в payment_id
    referral_discount = 0
    if user_id:
        try:
            from core.database import db
            referral_info = db.get_referral_info(user_id)
            if referral_info and referral_info.get('referral_balance', 0) > 0:
                referral_discount = referral_info['referral_balance']
        except:
            referral_discount = 0
    
    # Генерируем идентификатор платежа с информацией о скидке
    if user_id:
        timestamp = int(time.time())
        payment_id = f"bot_{user_id}_{tariff_type}_{referral_discount}_{timestamp}"
    else:
        payment_id = f"bot_unknown_{tariff_type}_0_{int(time.time())}"
    
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
        [InlineKeyboardButton(text="Получить помощь 💬", url="https://t.me/zabotasolo")],
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

def get_kupi_video_menu():
    """Меню для купи-видео"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Выбрать Тариф", callback_data="subscribe")],
        [InlineKeyboardButton(text="🔥 Служба Заботы", url="https://t.me/zabotasolo")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])