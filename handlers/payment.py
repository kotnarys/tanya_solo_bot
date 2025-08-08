import os
import logging
from aiogram import Router, Bot
from aiogram.types import FSInputFile
from keyboards.inline import get_documents_menu
from core.config import TEXTS, DOCUMENTS, DOCUMENT_LINKS
from utils.message_utils import send_split_message

logger = logging.getLogger(__name__)

router = Router()

async def send_payment_success(bot: Bot, user_id: int, tariff_name: str, referral_discount: int = 0):
    """
    Отправка сообщения об успешной оплате с документами
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        tariff_name: Название тарифа
        referral_discount: Сумма реферальной скидки для списания
    """
    
    try:
        # Списываем реферальные бонусы, если была скидка
        discount_text = ""
        if referral_discount > 0:
            try:
                from core.database import db
                if db.use_referral_balance(user_id, referral_discount):
                    logger.info(f"Списано {referral_discount} руб. реферального баланса у пользователя {user_id}")
                    discount_text = f"\n\n💰 Применена реферальная скидка: {referral_discount} ₽"
                else:
                    logger.warning(f"Не удалось списать реферальный баланс {referral_discount} руб. у пользователя {user_id}")
            except Exception as e:
                logger.error(f"Ошибка списания реферального баланса для {user_id}: {e}")
        
        # Отправляем сообщение об успешной оплате
        success_text = f"{TEXTS['payment_success']}\n\n🎯 Активирован тариф: «{tariff_name}»{discount_text}"
        await send_split_message(bot, success_text, user_id)
        
        # Отправляем документы
        await send_documents(bot, user_id)
        
        # Отправляем информацию о дополнительных документах
        await send_split_message(
            bot, 
            TEXTS['documents_info'],
            user_id,
            reply_markup=get_documents_menu()
        )
        
        # Отправляем супер новости новому подписчику
        try:
            from send_super_novosti import send_super_novosti_to_new_subscriber
            await send_super_novosti_to_new_subscriber(user_id)
            logger.info(f"Супер новости отправлены новому подписчику {user_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки супер новостей новому подписчику {user_id}: {e}")

        # Начисляем реферальный бонус, если это первая оплата
        try:
            from handlers.referral import add_referral_bonus_if_needed
            await add_referral_bonus_if_needed(user_id)
        except Exception as e:
            logger.error(f"Ошибка начисления реферального бонуса для {user_id}: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения об успешной оплате пользователю {user_id}: {e}")

async def send_documents(bot: Bot, user_id: int):
    """
    Отправка документов пользователю
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
    """
    
    # Отправляем оферту
    oferta_path = DOCUMENTS["oferta"]
    if os.path.exists(oferta_path):
        try:
            oferta_file = FSInputFile(oferta_path)
            await bot.send_document(
                user_id, 
                oferta_file, 
                caption="📄 Публичная оферта"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки оферты пользователю {user_id}: {e}")
    else:
        logger.error(f"Файл оферты не найден: {oferta_path}")
    
    # Отправляем согласие на обработку данных
    personal_data_path = DOCUMENTS["personal_data"]
    if os.path.exists(personal_data_path):
        try:
            personal_data_file = FSInputFile(personal_data_path)
            await bot.send_document(
                user_id, 
                personal_data_file, 
                caption="📄 Согласие на обработку персональных данных"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки согласия на обработку данных пользователю {user_id}: {e}")
    else:
        logger.error(f"Файл согласия на обработку данных не найден: {personal_data_path}")

# Функция для обработки webhook от GetCourse
async def process_payment_webhook(bot: Bot, webhook_data: dict):
    """
    Обработка webhook о статусе платежа от GetCourse
    
    Args:
        bot: Экземпляр бота
        webhook_data: Данные webhook
    """
    from utils.getcourse import validate_payment_webhook
    # Функции теперь встроены в main.py
    from main import extract_payment_info_from_payment_id, extract_user_id_from_webhook_data
    
    # Сначала пытаемся получить подробную информацию из payment_id
    payment_info = None
    
    # Ищем payment_id в различных полях webhook
    possible_fields = [
        'user_comment', 'comment', 'custom_field', 'utm_source',
        'description', 'product_name', 'order_comment', 'client_comment'
    ]
    
    for field in possible_fields:
        payment_id = webhook_data.get(field)
        if payment_id:
            payment_info = extract_payment_info_from_payment_id(payment_id)
            if payment_info:
                break
    
    # Fallback к старому методу если не удалось извлечь из payment_id
    if not payment_info:
        legacy_payment_info = validate_payment_webhook(webhook_data)
        if legacy_payment_info:
            payment_info = {
                'user_id': legacy_payment_info["user_id"],
                'tariff': legacy_payment_info["tariff"],
                'referral_discount': 0
            }
    
    if payment_info and webhook_data.get("status") == "success":
        user_id = payment_info["user_id"]
        tariff = payment_info["tariff"]
        referral_discount = payment_info.get("referral_discount", 0)
        
        # Определяем название тарифа
        if tariff == "basic":
            tariff_name = "Для себя"
        elif tariff == "vip":
            tariff_name = "ВИП Жизнь"  
        elif tariff == "course":
            tariff_name = "Курс"
        else:
            tariff_name = "Неизвестный тариф"
        
        # Отправляем сообщение об успешной оплате с информацией о скидке
        await send_payment_success(bot, user_id, tariff_name, referral_discount)
        
        logger.info(f"Обработан успешный платеж: пользователь {user_id}, тариф {tariff_name}, скидка {referral_discount} руб.")
    else:
        logger.warning(f"Webhook не обработан или статус платежа не успешный: {webhook_data}")