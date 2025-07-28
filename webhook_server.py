from flask import Flask, request, jsonify
import requests
import logging
from datetime import datetime
from config import BOT_TOKEN, ADMIN_IDS
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Текст сообщения покупателю после оплаты
CUSTOMER_SUCCESS_MESSAGE = """🎉 <b>Поздравляю!</b>

✨ Уже с <b>1 августа</b> откроются все функции ИИ Татьяны Соло

💫 Вас ждет невероятная трансформация!"""

# Текст при неуспешной оплате
CUSTOMER_FAILED_MESSAGE = """😔 <b>Ой, оплата не прошла</b>

💳 Попробуйте еще раз

Если проблема повторяется, обратитесь в службу заботы @zabotasolo"""

def extract_user_id_from_payment_id(payment_id):
    """Извлекает user_id из нашего идентификатора"""
    try:
        if payment_id and payment_id.startswith("bot_"):
            parts = payment_id.split("_")
            if len(parts) >= 2:
                return int(parts[1])
    except (ValueError, IndexError):
        logger.error(f"Не удалось извлечь user_id из payment_id: {payment_id}")
    return None

def send_telegram_message(user_id, message):
    """Отправка сообщения через Telegram Bot API (синхронно)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    data = {
        "chat_id": user_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Сообщение отправлено пользователю {user_id}")
            return True
        else:
            logger.error(f"❌ Ошибка отправки пользователю {user_id}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
        return False

def get_user_info(user_id):
    """Получение информации о пользователе"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    
    data = {"chat_id": user_id}
    
    try:
        response = requests.post(url, json=data, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            user_data = result.get("result", {})
            username = user_data.get("username")
            first_name = user_data.get("first_name", "")
            last_name = user_data.get("last_name", "")
            
            if username:
                return f"@{username}"
            elif first_name or last_name:
                return f"{first_name} {last_name}".strip()
            else:
                return f"ID: {user_id}"
        else:
            return f"ID: {user_id}"
            
    except Exception as e:
        logger.error(f"Ошибка получения информации о пользователе {user_id}: {e}")
        return f"ID: {user_id}"

def send_customer_success_message(user_id, tariff_name):
    """Отправка поздравления покупателю"""
    message = f"{CUSTOMER_SUCCESS_MESSAGE}\n\n🎯 <b>Ваш тариф:</b> {tariff_name}"
    return send_telegram_message(user_id, message)

def send_customer_failed_message(user_id, tariff_name):
    """Отправка сообщения о неуспешной оплате"""
    return send_telegram_message(user_id, CUSTOMER_FAILED_MESSAGE)

def send_admin_notifications(user_id, tariff_name):
    """Отправка уведомлений админам"""
    try:
        logger.info(f"Начинаем отправку уведомлений админам. ADMIN_IDS: {ADMIN_IDS}")
        
        if not ADMIN_IDS:
            logger.warning("ADMIN_IDS пустой!")
            return False
        
        # Получаем информацию о пользователе
        user_info = get_user_info(user_id)
        
        notification = f"""🔔 <b>НОВАЯ ОПЛАТА!</b>

👤 <b>Пользователь:</b> {user_info}
🎯 <b>Тариф:</b> {tariff_name}
🆔 <b>Telegram ID:</b> {user_id}
💳 <b>Статус:</b> Оплачено
📅 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
        
        sent_count = 0
        for admin_id in ADMIN_IDS:
            logger.info(f"Отправляем уведомление админу {admin_id}")
            if send_telegram_message(admin_id, notification):
                sent_count += 1
        
        logger.info(f"Отправлено {sent_count} из {len(ADMIN_IDS)} уведомлений")
        return sent_count > 0
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений админам: {e}")
        return False

@app.route('/webhook/getcourse', methods=['POST'])
def getcourse_webhook():
    """Обработка webhook от GetCourse"""
    try:
        data = request.get_json()
        logger.info(f"Получен webhook от GetCourse: {data}")
        
        # Ищем наш идентификатор
        payment_id = (
            data.get('user_comment') or 
            data.get('comment') or 
            data.get('custom_field') or
            data.get('utm_source')
        )
        
        user_id = extract_user_id_from_payment_id(payment_id)
        
        if user_id:
            # Определяем название тарифа
            tariff_name = "Неизвестный тариф"
            if payment_id:
                if "_basic_" in payment_id:
                    tariff_name = "«Для себя»"
                elif "_vip_" in payment_id:
                    tariff_name = "«ВИП Жизнь»"
            
            # Проверяем статус платежа
            status = data.get('status', '').lower()
            payment_status = data.get('payment_status', '').lower()
            
            is_success = (
                status in ['success', 'paid', 'completed'] or 
                payment_status in ['success', 'paid', 'completed']
            )
            
            is_failed = (
                status in ['failed', 'error', 'declined', 'cancelled'] or
                payment_status in ['failed', 'error', 'declined', 'cancelled']
            )
            
            if is_success:
                # Успешная оплата
                customer_sent = send_customer_success_message(user_id, tariff_name)
                admin_sent = send_admin_notifications(user_id, tariff_name)
                
                return jsonify({
                    "status": "success", 
                    "message": "Уведомления о успешной оплате отправлены",
                    "customer_notified": customer_sent,
                    "admins_notified": admin_sent
                })
                
            elif is_failed:
                # Неуспешная оплата
                customer_sent = send_customer_failed_message(user_id, tariff_name)
                
                return jsonify({
                    "status": "failed", 
                    "message": "Уведомление о неуспешной оплате отправлено",
                    "customer_notified": customer_sent
                })
            else:
                # Неизвестный статус
                logger.info(f"Неизвестный статус платежа: {data.get('status')}")
                return jsonify({"status": "ignored", "message": "Неизвестный статус платежа"})
        else:
            logger.warning(f"Не удалось извлечь user_id из webhook: {data}")
            return jsonify({"status": "error", "message": "User ID не найден"})
            
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервера"""
    return jsonify({"status": "ok", "message": "Webhook server is running"})

if __name__ == '__main__':
    logger.info("Запуск webhook сервера...")
    app.run(host='0.0.0.0', port=5000, debug=False)