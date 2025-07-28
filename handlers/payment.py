import os
from aiogram import Router, Bot
from aiogram.types import FSInputFile
from keyboards.inline import get_documents_menu
from config import TEXTS, DOCUMENTS, DOCUMENT_LINKS

router = Router()

async def send_payment_success(bot: Bot, user_id: int, tariff_name: str):
    """
    Отправка сообщения об успешной оплате с документами
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        tariff_name: Название тарифа
    """
    
    try:
        # Отправляем сообщение об успешной оплате
        success_text = f"{TEXTS['payment_success']}\n\n🎯 Активирован тариф: «{tariff_name}»"
        await bot.send_message(user_id, success_text)
        
        # Отправляем документы
        await send_documents(bot, user_id)
        
        # Отправляем информацию о дополнительных документах
        await bot.send_message(
            user_id, 
            TEXTS['documents_info'], 
            reply_markup=get_documents_menu()
        )
        
    except Exception as e:
        print(f"Ошибка при отправке сообщения об успешной оплате пользователю {user_id}: {e}")

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
            print(f"Ошибка отправки оферты пользователю {user_id}: {e}")
    else:
        print(f"Файл оферты не найден: {oferta_path}")
    
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
            print(f"Ошибка отправки согласия на обработку данных пользователю {user_id}: {e}")
    else:
        print(f"Файл согласия на обработку данных не найден: {personal_data_path}")

# Функция для обработки webhook от GetCourse
async def process_payment_webhook(bot: Bot, webhook_data: dict):
    """
    Обработка webhook о статусе платежа от GetCourse
    
    Args:
        bot: Экземпляр бота
        webhook_data: Данные webhook
    """
    from utils.getcourse import validate_payment_webhook
    
    # Валидируем данные webhook
    payment_info = validate_payment_webhook(webhook_data)
    
    if payment_info and webhook_data.get("status") == "success":
        user_id = payment_info["user_id"]
        tariff = payment_info["tariff"]
        
        # Определяем название тарифа
        tariff_name = "Для себя" if tariff == "basic" else "ВИП Жизнь"
        
        # Отправляем сообщение об успешной оплате
        await send_payment_success(bot, user_id, tariff_name)
        
        print(f"Обработан успешный платеж: пользователь {user_id}, тариф {tariff_name}")
    else:
        print(f"Webhook не обработан или статус платежа не успешный: {webhook_data}")