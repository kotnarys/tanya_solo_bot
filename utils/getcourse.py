import requests
import json
import base64
import time
from config import GETCOURSE_API_URL, GETCOURSE_API_KEY

async def create_payment_link(user_id: int, tariff: str, price: int, tariff_name: str, user_data: dict):
    """
    Создание ссылки на оплату через API GetCourse
    
    Args:
        user_id: ID пользователя в Telegram
        tariff: Тип тарифа (basic/vip)
        price: Цена тарифа
        tariff_name: Название тарифа
        user_data: Данные пользователя (email, name, phone)
    
    Returns:
        str: Ссылка на оплату или None в случае ошибки
    """
    
    # Генерируем уникальный идентификатор для отслеживания
    payment_id = f"bot_{user_id}_{tariff}_{int(time.time())}"
    
    # Параметры для создания заказа в GetCourse
    params = {
        "user": {
            "email": user_data.get("email"),
            "phone": user_data.get("phone", "+7xxxxxxxxxx"), 
            "name": user_data.get("name", f"User_{user_id}")
        },
        "system": {
            "refresh_if_exists": 1  # Обновить пользователя, если уже существует
        },
        "deal": {
            "deal_cost": price,
            "deal_currency": "rub",
            "product_title": f"Онлайн-аватар Татьяны Соло - {tariff_name}",
            # Наш идентификатор сохраняем в комментарии
            "user_comment": payment_id
        }
    }
    
    try:
        # Кодируем параметры в base64
        params_encoded = base64.b64encode(json.dumps(params).encode()).decode()
        
        # Данные для POST-запроса
        data = {
            "key": GETCOURSE_API_KEY,
            "action": "deals/create", 
            "params": params_encoded
        }
        
        # Отправляем запрос
        response = requests.post(GETCOURSE_API_URL, data=data)
        result = response.json()
        
        # Проверяем успешность
        if result.get("success") == "true" and result.get("result", {}).get("success") == "true":
            payment_link = result["result"].get("payment_link")
            
            if payment_link:
                print(f"Создана ссылка на оплату для пользователя {user_id}, тариф {tariff}, ID: {payment_id}")
                return payment_link
            else:
                print(f"GetCourse вернул успех, но без ссылки на оплату: {result}")
                return None
        else:
            error_message = result.get("result", {}).get("error_message", "Неизвестная ошибка")
            print(f"Ошибка создания заказа в GetCourse: {error_message}")
            print(f"Полный ответ: {result}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети при запросе к GetCourse: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON ответа от GetCourse: {e}")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка при работе с GetCourse API: {e}")
        return None

def validate_payment_webhook(webhook_data: dict) -> dict:
    """
    Валидация webhook от GetCourse о статусе платежа
    
    Args:
        webhook_data: Данные webhook
        
    Returns:
        dict: Обработанные данные платежа или None
    """
    try:
        # Извлекаем наш идентификатор из комментария
        user_comment = webhook_data.get("user_comment", "")
        
        if user_comment.startswith("bot_"):
            parts = user_comment.split("_")
            if len(parts) >= 4:
                user_id = int(parts[1])
                tariff = parts[2]
                timestamp = parts[3]
                
                return {
                    "user_id": user_id,
                    "tariff": tariff,
                    "timestamp": timestamp,
                    "payment_id": user_comment,
                    "deal_id": webhook_data.get("deal_id"),
                    "status": webhook_data.get("status", "unknown")
                }
        
        return None
        
    except (ValueError, IndexError) as e:
        print(f"Ошибка парсинга webhook данных: {e}")
        return None