import asyncio
import logging
import os
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import threading
from flask import Flask, request, jsonify
import requests
from datetime import datetime
from collections import defaultdict
import time

from core.config import BOT_TOKEN, ADMIN_IDS
from handlers import start, info, tariffs, support, payment, subscription, ai_chat, referral, news
from background.auto_spam import start_auto_spam_task
from core.database import init_db, db
from background.kupi_video import kupi_video_background_task
from background.daily_thread_reset import daily_thread_reset_task

# Настройка логирования - только критические ошибки
logging.basicConfig(
    level=logging.CRITICAL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Отключаем лишние логи
logging.getLogger('handlers.ai_chat').setLevel(logging.CRITICAL)
logging.getLogger('core.openai_client').setLevel(logging.CRITICAL)
logging.getLogger('background.kupi_video').setLevel(logging.CRITICAL)
logging.getLogger('background.auto_spam').setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)

# =================== WEBHOOK SERVER ===================

# Подавляем лишние логи от werkzeug (Flask)
class NoBotsLogFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            if '404' in message and any(path in message for path in 
                ['GET /', 'GET /favicon.ico', 'GET /login', 'GET /signin', 'GET /admin']):
                return False
            if 'Bad request' in message and ('À' in message or 'SSH-2.0' in message):
                return False
            if 'HTTP/2.0' in message:
                return False
        return True

# Применяем фильтр к werkzeug logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(NoBotsLogFilter())
werkzeug_logger.setLevel(logging.ERROR)

app = Flask(__name__)

# Rate limiting
request_counts = defaultdict(list)
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60

def is_rate_limited(ip):
    now = time.time()
    request_counts[ip] = [req_time for req_time in request_counts[ip] if now - req_time < RATE_LIMIT_WINDOW]
    if len(request_counts[ip]) >= RATE_LIMIT_REQUESTS:
        return True
    request_counts[ip].append(now)
    return False

def extract_payment_info_from_payment_id(payment_id):
    try:
        if payment_id and payment_id.startswith("bot_"):
            parts = payment_id.split("_")
            if len(parts) == 5:
                discount_value = int(parts[3]) if parts[3].isdigit() else 0
                if discount_value % 500 != 0:
                    discount_value = 0
                return {
                    'user_id': int(parts[1]),
                    'tariff': parts[2],
                    'referral_discount': discount_value
                }
            elif len(parts) == 4:
                return {
                    'user_id': int(parts[1]),
                    'tariff': parts[2],
                    'referral_discount': 0
                }
            elif len(parts) >= 2:
                return {
                    'user_id': int(parts[1]),
                    'tariff': parts[2] if len(parts) > 2 else 'basic',
                    'referral_discount': 0
                }
    except (ValueError, IndexError):
        logger.error(f"Не удалось извлечь данные из payment_id: {payment_id}")
    return None

def extract_user_id_from_webhook_data(data):
    possible_fields = [
        'user_comment', 'comment', 'custom_field', 'utm_source',
        'description', 'product_name', 'order_comment', 'client_comment'
    ]
    for field in possible_fields:
        payment_id = data.get(field)
        if payment_id:
            payment_info = extract_payment_info_from_payment_id(payment_id)
            if payment_info:
                return payment_info['user_id'], payment_id
    return None, None

def send_telegram_message(user_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": user_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
        return False

def get_user_info(user_id):
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
        return f"ID: {user_id}"
    except:
        return f"ID: {user_id}"

@app.route('/webhook/getcourse', methods=['POST'])
def getcourse_webhook():
    print(f"WEBHOOK: Получен запрос: {request.method} {request.url}")
    try:
        data = request.get_json()
        print(f"WEBHOOK: Данные - {data}")
        user_id, payment_id = extract_user_id_from_webhook_data(data)
        
        if user_id:
            status = data.get('status', '').lower()
            payment_status = data.get('payment_status', '').lower()
            
            is_success = (
                status in ['success', 'paid', 'completed'] or 
                payment_status in ['success', 'paid', 'completed']
            )
            
            if is_success:
                # Определяем тариф
                if "_basic_" in payment_id:
                    tariff_type = "basic"
                    tariff_name = "«Для себя»"
                elif "_vip_" in payment_id:
                    tariff_type = "vip"
                    tariff_name = "«ВИП Жизнь»"
                elif "_course_" in payment_id:
                    tariff_type = "course"
                    tariff_name = "«Курс»"
                else:
                    tariff_type = "unknown"
                    tariff_name = "Неизвестный тариф"
                
                # Сохраняем подписку
                try:
                    db.save_subscription(user_id, tariff_type, payment_id)
                except Exception as e:
                    logger.error(f"Ошибка сохранения подписки: {e}")
                
                # Уведомления
                success_msg = f"""🎉 <b>Поздравляем! Ваша оплата прошла успешно!</b>

✅ Доступ к онлайн-аватару Татьяны Соло активирован

🎯 <b>Ваш тариф:</b> {tariff_name}"""
                
                send_telegram_message(user_id, success_msg)
                
                # Уведомления админам
                if ADMIN_IDS:
                    user_info = get_user_info(user_id)
                    admin_msg = f"""🔔 <b>НОВАЯ ОПЛАТА!</b>

👤 <b>Пользователь:</b> {user_info}
🎯 <b>Тариф:</b> {tariff_name}
🆔 <b>Telegram ID:</b> {user_id}
💳 <b>Статус:</b> Оплачено
📅 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
                    
                    for admin_id in ADMIN_IDS:
                        send_telegram_message(admin_id, admin_msg)
                
                # Реферальные бонусы
                try:
                    payment_info = extract_payment_info_from_payment_id(payment_id)
                    referral_discount = payment_info.get('referral_discount', 0) if payment_info else 0
                    
                    if referral_discount > 0:
                        db.use_referral_balance(user_id, referral_discount)
                        
                    # Начисляем бонус рефереру
                    from handlers.referral import add_referral_bonus_if_needed
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(add_referral_bonus_if_needed(user_id))
                    finally:
                        loop.close()
                        
                except Exception as e:
                    logger.error(f"Ошибка реферальных бонусов: {e}")
                
                return jsonify({"status": "success", "message": "Подписка сохранена"})
        
        return jsonify({"status": "ignored", "message": "No valid payment data"})
        
    except Exception as e:
        logger.error(f"Ошибка webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    if is_rate_limited(client_ip):
        return jsonify({"error": "Rate limit exceeded"}), 429
    return jsonify({
        "service": "Tatyana Solo Bot",
        "status": "running"
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

def run_webhook_server():
    """Запуск webhook сервера в отдельном потоке"""
    try:
        print("Webhook сервер стартует на 0.0.0.0:8080")
        app.run(host='0.0.0.0', port=8080, debug=False)
    except Exception as e:
        print(f"ОШИБКА webhook сервера: {e}")

# =================== END WEBHOOK SERVER ===================

async def system_check():
    """Проверка системы при запуске"""
    errors = []
    
    # Проверка токена бота
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN не установлен")
    
    # Проверка структуры папок
    required_dirs = ['media/images', 'media/videos', 'media/documents', 'media/otziv']
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            errors.append(f"Папка {dir_path} не найдена")
    
    # Предупреждение о купи-видео (не критичная ошибка)
    kupi_video_path = "media/video/kupi.mp4"
    if not Path(kupi_video_path).exists():
        print(f"⚠️  ПРЕДУПРЕЖДЕНИЕ: Купи-видео не найдено: {kupi_video_path}")
        print("   Система будет работать, но купи-видео не будет отправляться")
    
    # Проверка базы данных
    try:
        init_db()
    except Exception as e:
        errors.append(f"Ошибка инициализации БД: {e}")
    
    # Проверка импортов модулей
    try:
        from core.config import TEXTS, TARIFF_BASIC_PRICE, TARIFF_VIP_PRICE
        if not TEXTS:
            errors.append("Конфигурация TEXTS пуста")
    except ImportError as e:
        errors.append(f"Ошибка импорта конфигурации: {e}")
    
    if errors:
        print("ОБНАРУЖЕНЫ ОШИБКИ ПРИ ЗАПУСКЕ:")
        for error in errors:
            print(f"  {error}")
        print()
        return False
    else:
        print("Все системные проверки пройдены успешно")
        return True

async def main():
    """Основная функция запуска бота"""
    
    # Проверка системы перед запуском
    if not await system_check():
        print("Запуск прерван из-за ошибок системы")
        return
    
    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализация диспетчера
    dp = Dispatcher()
    
    # Подключение роутеров
    dp.include_router(start.router)
    dp.include_router(info.router)
    dp.include_router(tariffs.router)
    dp.include_router(support.router)
    dp.include_router(payment.router)
    dp.include_router(subscription.router)
    dp.include_router(referral.router)
    dp.include_router(news.router)  # Админ панель для рассылки новостей
    # AI чат должен быть последним, чтобы перехватывать все остальные сообщения
    dp.include_router(ai_chat.router)
    
    # Запуск webhook сервера в отдельном потоке
    webhook_thread = threading.Thread(target=run_webhook_server, daemon=True)
    webhook_thread.start()
    print("Webhook сервер запущен на порту 8080")
    
    # Запуск фоновых задач
    auto_spam_task = asyncio.create_task(start_auto_spam_task(bot))
    kupi_video_task = asyncio.create_task(kupi_video_background_task(bot))
    daily_reset_task = asyncio.create_task(daily_thread_reset_task())
    
    # Запуск бота
    print("Telegram бот запущен и работает...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка при работе бота: {e}")
        print(f"Критическая ошибка: {e}")
    finally:
        # Отменяем фоновые задачи
        auto_spam_task.cancel()
        kupi_video_task.cancel()
        daily_reset_task.cancel()
        try:
            await auto_spam_task
        except asyncio.CancelledError:
            pass
        try:
            await kupi_video_task
        except asyncio.CancelledError:
            pass
        try:
            await daily_reset_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        print("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())