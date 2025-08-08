# utm_manager.py
"""
Менеджер UTM меток пользователей - работа с базой данных и памятью
"""
from core.database import db

# Кеш UTM меток в памяти для быстрого доступа
utm_cache = {}

# Кеш отправленных видео
video_sent_cache = {}

def parse_utm_from_start(start_param: str) -> dict:
    """
    Парсит UTM метки из параметра /start
    
    Поддерживает два формата:
    1. "welcome2025_utm_source-ig_utm_medium-stories_utm_campaign-avatarai"
    2. "welcome2025?utm_source=ig&utm_medium=stories&utm_campaign=avatarai"
    
    Args:
        start_param: параметр из команды /start
        
    Returns:
        dict: UTM метки {"utm_source": "ig", "utm_medium": "stories", "utm_campaign": "avatarai"}
    """
    if not start_param:
        return {}
    
    if not (start_param.startswith("welcome2025") or start_param.startswith("w25")):
        return {}
    
    try:
        utm_data = {}
        
        # Формат 1: с вопросительным знаком (welcome2025?utm_source=ig&utm_medium=stories&utm_campaign=avatarai)
        if "?" in start_param:
            parts = start_param.split("?", 1)
            if len(parts) == 2:
                utm_string = parts[1]
                utm_params = utm_string.split("&")
                
                for param in utm_params:
                    if "=" in param:
                        key, value = param.split("=", 1)
                        if key.startswith("utm_"):
                            utm_data[key] = value
        
        # Формат 2: с подчеркиваниями (welcome2025_utm_source-ig_utm_medium-stories_utm_campaign-avatarai)
        elif "_" in start_param:
            # Убираем префиксы
            if start_param.startswith("welcome2025_"):
                utm_string = start_param.replace("welcome2025_", "")
            elif start_param.startswith("w25_"):
                utm_string = start_param.replace("w25_", "")
            else:
                utm_string = start_param
            
            # Разбиваем на части по символу "_"
            utm_parts = utm_string.split("_")
            
            # Сокращения для коротких форматов
            short_map = {
                "s": "utm_source",
                "m": "utm_medium", 
                "c": "utm_campaign"
            }
            
            for part in utm_parts:
                if "-" in part:
                    # Разбиваем "s-ig" на ["s", "ig"]
                    key, value = part.split("-", 1)
                    
                    # Преобразуем короткие ключи в полные
                    if key in short_map:
                        key = short_map[key]
                    elif not key.startswith("utm_"):
                        key = f"utm_{key}"
                    
                    utm_data[key] = value
        
        return utm_data
        
    except Exception as e:
        return {}

def save_utm_to_cache_and_db(user_id: int, utm_data: dict):
    """
    Сохраняет UTM метки в кеш и базу данных
    
    Args:
        user_id: ID пользователя
        utm_data: UTM метки
    """
    if not utm_data:
        return
    
    # Сохраняем в кеш
    utm_cache[user_id] = utm_data
    
    # Сохраняем в базу данных
    try:
        db.save_user_utm(user_id, utm_data)
    except Exception as e:
        pass

def get_utm_from_cache_or_db(user_id: int) -> dict:
    """
    Получает UTM метки из кеша или базы данных
    
    Args:
        user_id: ID пользователя
        
    Returns:
        dict: UTM метки или пустой словарь
    """
    # Сначала проверяем в кеше
    if user_id in utm_cache:
        return utm_cache[user_id]
    
    # Если в кеше нет, загружаем из БД
    try:
        utm_data = db.get_user_utm(user_id)
        if utm_data:
            # Кешируем для следующих обращений
            utm_cache[user_id] = utm_data
            return utm_data
        else:
            return {}
    except Exception as e:
        return {}

def build_utm_url_params(utm_data: dict) -> str:
    """
    Строит строку UTM параметров для URL
    
    Args:
        utm_data: UTM метки
        
    Returns:
        str: строка для URL "utm_source=ig&utm_medium=stories&utm_campaign=avatarai"
    """
    if not utm_data:
        # Дефолтные UTM метки если пользовательских нет
        default_params = "utm_source=telegram_bot&utm_medium=button&utm_campaign=avatarai"
        return default_params
    
    utm_params = []
    for key, value in utm_data.items():
        if key and value:  # Проверяем что ключ и значение не пустые
            utm_params.append(f"{key}={value}")
    
    utm_string = "&".join(utm_params)
    return utm_string

def get_utm_url_params_for_user(user_id: int) -> str:
    """
    Получает готовую строку UTM параметров для конкретного пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        str: UTM параметры для URL
    """
    utm_data = get_utm_from_cache_or_db(user_id)
    return build_utm_url_params(utm_data)

# ===== ФУНКЦИИ ДЛЯ ВИДЕО =====

def is_video_already_sent(user_id: int) -> bool:
    """
    Проверяет, было ли уже отправлено видео пользователю
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True если видео уже отправлялось
    """
    return video_sent_cache.get(user_id, False)

def mark_video_as_sent(user_id: int):
    """
    Отмечает, что видео было отправлено пользователю
    
    Args:
        user_id: ID пользователя
    """
    video_sent_cache[user_id] = True

# ===== ОСНОВНЫЕ ФУНКЦИИ ДЛЯ ИМПОРТА =====

def parse_and_save_utm(user_id: int, start_param: str):
    """
    Основная функция: парсит и сохраняет UTM метки пользователя
    
    Args:
        user_id: ID пользователя
        start_param: параметр из /start
    """
    utm_data = parse_utm_from_start(start_param)
    if utm_data:
        save_utm_to_cache_and_db(user_id, utm_data)

def get_payment_url_with_utm(user_id: int, base_url: str, payment_id: str) -> str:
    """
    Строит полную ссылку на оплату с UTM метками пользователя
    
    Args:
        user_id: ID пользователя
        base_url: базовая ссылка (например: "https://solotatiana.getcourse.ru/avatarself")
        payment_id: ID платежа
        
    Returns:
        str: полная ссылка с UTM метками
    """
    utm_data = get_utm_from_cache_or_db(user_id)
    utm_params = get_utm_url_params_for_user(user_id)
    full_url = f"{base_url}?id={payment_id}&{utm_params}"
    
    
    return full_url