import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot
from aiogram.types import FSInputFile
from core.database import db
from keyboards.inline import get_kupi_video_menu
from utils.message_utils import send_split_message

logger = logging.getLogger(__name__)

def get_kupi_content():
    """
    Возвращает путь к видео и текст в зависимости от текущей даты
    
    Returns:
        tuple: (video_path, text_content)
    """
    # Московское время
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)
    
    # Определяем какие файлы использовать
    if now.date() < datetime(2025, 7, 30).date():
        # До 30.07.2025 - используем оригинальные файлы
        video_path = "media/video/kupi.mp4"
        text_content = """🎁 <b>ТОЛЬКО СЕГОДНЯ до 23:59 по мск ПОДАРОК:</b>

💫 8D-практика «Наполнение энергией космоса» (<s>7000₽</s>)

А еще <b>самая низкая цена</b> на подключение к ИИ Тане Соло на <b>целый месяц!</b>

⏰ <b>Успевай</b>, чтобы не упустить возможность, нажимай «<b>Выбрать Тариф</b>»

А если нужна помощь, выбери кнопку «<b>Служба Заботы</b>"""
    elif now.date() == datetime(2025, 7, 30).date():
        # 30.07.2025 - используем kupi1
        video_path = "media/video/kupi1.mp4"
        text_content = load_text_from_file("media/video/kupi1.txt")
    else:
        # 31.07.2025 и далее - используем kupi2
        video_path = "media/video/kupi2.mp4"
        text_content = load_text_from_file("media/video/kupi2.txt")
    
    return video_path, text_content

def reset_kupi_history_if_needed():
    """
    Сбрасывает историю отправки купи-видео для новых дат (30.07 и 31.07)
    чтобы всем пользователям отправилось заново
    """
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)
    current_date = now.date()
    
    # Даты, когда нужно сбросить историю
    reset_dates = [
        datetime(2025, 7, 30).date(),  # 30.07.2025
        datetime(2025, 7, 31).date()   # 31.07.2025
    ]
    
    if current_date in reset_dates:
        try:
            # Проверяем, был ли уже сброс сегодня
            reset_key = f"kupi_reset_{current_date.strftime('%Y-%m-%d')}"
            
            # Простая проверка через файл-маркер
            reset_marker_file = f"media/video/{reset_key}.marker"
            
            if not os.path.exists(reset_marker_file):
                # Сбрасываем историю отправки купи-видео
                db.reset_kupi_video_history()
                
                # Создаем маркер, что сброс уже был сегодня
                with open(reset_marker_file, 'w') as f:
                    f.write(f"Reset done at {now.isoformat()}")
                
                logger.info(f"История купи-видео сброшена для даты {current_date}")
            else:
                logger.debug(f"История купи-видео уже была сброшена для даты {current_date}")
                
        except Exception as e:
            logger.error(f"Ошибка сброса истории купи-видео: {e}")

def load_text_from_file(file_path):
    """
    Загружает текст из файла с правильной кодировкой
    
    Args:
        file_path: путь к текстовому файлу
        
    Returns:
        str: содержимое файла или резервный текст при ошибке
    """
    try:
        # Сначала пробуем UTF-8
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except UnicodeDecodeError:
            # Если не получается, пробуем UTF-16
            with open(file_path, 'r', encoding='utf-16') as f:
                return f.read().strip()
    except Exception as e:
        logger.error(f"Ошибка загрузки текста из {file_path}: {e}")
        # Возвращаем резервный текст
        return """🎁 <b>Специальное предложение!</b>

Выбирай тариф или пиши в Службу Заботы, если есть вопросы 👇🏻"""

async def send_kupi_video_to_user(bot: Bot, user_id: int) -> bool:
    """
    Отправляет купи-видео пользователю
    
    Args:
        bot: экземпляр бота
        user_id: ID пользователя
        
    Returns:
        bool: True если сообщение успешно отправлено
    """
    try:
        # Получаем актуальные пути и текст
        video_path, text_content = get_kupi_content()
        
        # Сначала пробуем отправить видеокружок, если файл существует
        if os.path.exists(video_path):
            try:
                # Проверяем размер файла (50 МБ лимит для видеокружков)
                file_size = os.path.getsize(video_path)
                max_size = 50 * 1024 * 1024  # 50 МБ
                
                if file_size <= max_size:
                    video = FSInputFile(video_path)
                    
                    # Пробуем отправить как видеокружок
                    try:
                        await bot.send_video_note(user_id, video, request_timeout=120)
                        logger.info(f"Купи-видеокружок отправлен пользователю {user_id}")
                    except Exception as e:
                        # Если у пользователя отключены голосовые/видео сообщения, отправляем как обычное видео
                        if "VOICE_MESSAGES_FORBIDDEN" in str(e):
                            video = FSInputFile(video_path)
                            await bot.send_video(user_id, video, request_timeout=120)
                            logger.info(f"Купи-видео отправлено как обычное видео пользователю {user_id} (видеокружки запрещены)")
                        else:
                            # Проверяем, заблокирован ли бот пользователем
                            if "bot was blocked by the user" in str(e) or "Forbidden" in str(e):
                                logger.debug(f"Пользователь {user_id} заблокировал бота, пропускаем")
                            else:
                                logger.warning(f"Не удалось отправить видео пользователю {user_id}: {e}")
                    
                    # Небольшая пауза перед отправкой текста
                    await asyncio.sleep(1)
                else:
                    logger.warning(f"Купи-видео слишком большое: {file_size / 1024 / 1024:.1f} МБ (максимум 50 МБ)")
            except Exception as e:
                logger.warning(f"Ошибка при работе с видео файлом: {e}")
        else:
            logger.info(f"Купи-видео не найдено: {video_path}, отправляем только текст")
        
        # Отправляем текст с кнопками
        await send_split_message(
            bot,
            text_content,
            user_id,
            reply_markup=get_kupi_video_menu()
        )
        
        # Отмечаем в БД что сообщение отправлено
        db.mark_kupi_video_sent(user_id, video_path if os.path.exists(video_path) else "text_only")
        logger.info(f"Купи-сообщение отправлено пользователю {user_id}")
        return True
        
    except Exception as e:
        # Проверяем, заблокирован ли бот пользователем
        error_message = str(e)
        if "bot was blocked by the user" in error_message or "Forbidden" in error_message:
            # Тихо логируем блокировку на уровне DEBUG
            logger.debug(f"Пользователь {user_id} заблокировал бота, пропускаем")
        else:
            # Для других ошибок логируем как ERROR
            logger.error(f"Ошибка отправки купи-сообщения пользователю {user_id}: {e}")
        return False

async def process_kupi_video_queue(bot: Bot):
    """
    Обрабатывает очередь пользователей для отправки купи-видео
    
    Args:
        bot: экземпляр бота
    """
    try:
        # Проверяем, нужно ли сбросить историю отправки для новых дат
        reset_kupi_history_if_needed()
        
        # Получаем пользователей, которым нужно отправить купи-видео
        users_to_send = db.get_users_for_kupi_video()
        
        if not users_to_send:
            logger.debug("Нет пользователей для отправки купи-видео")
            return
        
        logger.info(f"Начинаем отправку купи-видео для {len(users_to_send)} пользователей")
        
        success_count = 0
        error_count = 0
        
        for user_id in users_to_send:
            try:
                success = await send_kupi_video_to_user(bot, user_id)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                
                # Небольшая пауза между отправками
                await asyncio.sleep(1)
                
            except Exception as e:
                # Проверяем, заблокирован ли бот пользователем
                error_message = str(e)
                if "bot was blocked by the user" in error_message or "Forbidden" in error_message:
                    # Тихо логируем блокировку на уровне DEBUG
                    logger.debug(f"Пользователь {user_id} заблокировал бота, пропускаем")
                else:
                    # Для других ошибок логируем как ERROR
                    logger.error(f"Критическая ошибка при отправке купи-видео пользователю {user_id}: {e}")
                error_count += 1
        
        if success_count > 0 or error_count > 0:
            logger.info(f"Отправка купи-видео завершена. Успешно: {success_count}, Ошибок: {error_count}")
            
    except Exception as e:
        logger.error(f"Ошибка в процессе обработки очереди купи-видео: {e}")

async def kupi_video_background_task(bot: Bot):
    """
    Фоновая задача для периодической отправки купи-видео
    Запускается каждые 10 минут
    
    Args:
        bot: экземпляр бота
    """
    logger.info("Запущена фоновая задача купи-видео")
    
    while True:
        try:
            await process_kupi_video_queue(bot)
            
            # Ждем 10 минут до следующей проверки
            await asyncio.sleep(600)  # 10 минут = 600 секунд
            
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче купи-видео: {e}")
            # При ошибке ждем 5 минут и пробуем снова
            await asyncio.sleep(300)

async def test_send_kupi_video(bot: Bot, user_id: int):
    """
    Тестовая отправка купи-видео конкретному пользователю
    
    Args:
        bot: экземпляр бота
        user_id: ID пользователя для тестирования
    """
    logger.info(f"Тестовая отправка купи-видео пользователю {user_id}")
    
    # Получаем актуальный текст
    _, text_content = get_kupi_content()
    
    # Отправляем только текст с кнопками (без видео для теста)
    try:
        await send_split_message(
            bot,
            text_content,
            user_id,
            reply_markup=get_kupi_video_menu()
        )
        logger.info(f"Тестовое сообщение купи-видео отправлено пользователю {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка тестовой отправки купи-видео пользователю {user_id}: {e}")
        return False