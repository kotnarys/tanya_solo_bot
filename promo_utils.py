from datetime import datetime
from config import TEXTS

def get_promo_date():
    """
    Возвращает дату для промо акции в зависимости от текущей даты
    
    Returns:
        str: дата в формате "29.07" или "30.07" или None если акция закончилась
    """
    today = datetime.now()
    
    # 28 июля - показываем до 29.07
    if today.day == 28 and today.month == 7:
        return "29.07"
    # 29 июля - показываем до 30.07  
    elif today.day == 29 and today.month == 7:
        return "30.07"
    # После 29 июля - акция закончилась
    else:
        return None

def get_tariffs_text_with_promo():
    """
    Возвращает текст тарифов с промо или обычный текст тарифов
    
    Returns:
        str: текст для тарифов
    """
    promo_date = get_promo_date()
    
    if promo_date:
        return TEXTS["tariffs_intro_with_promo"].format(date=promo_date)
    else:
        return TEXTS["tariffs_intro"]

def should_show_promo():
    """
    Проверяет, нужно ли показывать промо акцию
    
    Returns:
        bool: True если нужно показать промо
    """
    return get_promo_date() is not None