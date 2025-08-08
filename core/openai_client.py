import asyncio
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenAI конфигурация
OPENAI_API_KEY = "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"
ASSISTANT_ID = "asst_9sI7k0guXxzcJp2z4fcaiJfx"

# Дата начала доступа к OpenAI для подписчиков
OPENAI_ACCESS_START_DATE = datetime(2025, 7, 30, 15, 0, 0)  # 30 июля 2025 15:00 МСК

# ID администраторов для отладки (они имеют доступ всегда) - УДАЛЕНО, используем PERMANENT_ACCESS_IDS из config
# ADMIN_IDS = [956895950, 530738541, 94398806]

class OpenAIClient:
    def __init__(self):
        self.client = None
        self.request_queue = asyncio.Queue(maxsize=10)  # Очередь запросов
        self.processing = False
    
    def _get_client(self):
        """Lazy initialization OpenAI клиента"""
        if self.client is None:
            try:
                import openai
                self.client = openai.OpenAI(
                    api_key=OPENAI_API_KEY,
                    timeout=30.0
                )
            except Exception as e:
                logger.error(f"Ошибка инициализации OpenAI клиента: {e}")
                return None
        return self.client
    
    def has_openai_access(self, user_id: int) -> bool:
        """
        Проверяет, есть ли у пользователя доступ к OpenAI
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если есть доступ
        """
        # Администраторы с вечным доступом имеют доступ всегда
        from core.config import PERMANENT_ACCESS_IDS
        if user_id in PERMANENT_ACCESS_IDS:
            return True
            
        # Проверяем дату - доступ только с 30 июля 15:00
        if datetime.now() < OPENAI_ACCESS_START_DATE:
            return False
            
        # Проверяем активную подписку
        from core.database import db
        return db.is_user_subscribed(user_id)
    
    async def create_thread(self, user_id: int) -> Optional[str]:
        """Создает новый thread для пользователя"""
        if not self.has_openai_access(user_id):
            return None
        
        client = self._get_client()
        if not client:
            return None
            
        try:
            thread = await asyncio.to_thread(client.beta.threads.create)
            logger.info(f"Создан новый thread {thread.id} для пользователя {user_id}")
            return thread.id
        except Exception as e:
            logger.error(f"Ошибка создания thread для пользователя {user_id}: {e}")
            return None
    
    async def send_message(self, user_id: int, thread_id: str, message: str) -> Optional[str]:
        """Отправляет сообщение в thread и получает ответ от ассистента"""
        if not self.has_openai_access(user_id):
            return None
        
        client = self._get_client()
        if not client:
            return None
        
        # Проверяем, нужно ли сбросить thread (ежедневный сброс в 00:00 МСК)
        from core.database import db
        thread_info = db.get_openai_thread(user_id)
        if thread_info and db.should_reset_thread_daily(user_id):
            logger.info(f"Ежедневный сброс thread для пользователя {user_id}")
            await self._reset_user_thread(user_id)
            # Создаем новый thread
            new_thread_id = await self.create_thread(user_id)
            if new_thread_id:
                db.save_openai_thread(user_id, new_thread_id)
                thread_id = new_thread_id
            else:
                # Возвращаем обычную ошибку без упоминания сброса
                return "😔 Что-то пошло не так... Попробуй написать еще раз через минутку 💕"
        
        # Добавляем задержку для rate limit
        await asyncio.sleep(2)
            
        try:
            # Сначала проверяем, нет ли активных runs
            runs = await asyncio.to_thread(
                client.beta.threads.runs.list,
                thread_id=thread_id,
                limit=1
            )
            
            # Если есть активный run - ждем его завершения
            if runs.data and runs.data[0].status in ['queued', 'in_progress', 'cancelling']:
                active_run = runs.data[0]
                logger.info(f"Ждем завершения активного run для пользователя {user_id}")
                
                # Ждем до 30 секунд
                wait_time = 0
                while active_run.status in ['queued', 'in_progress', 'cancelling'] and wait_time < 30:
                    await asyncio.sleep(2)
                    wait_time += 2
                    active_run = await asyncio.to_thread(
                        client.beta.threads.runs.retrieve,
                        thread_id=thread_id,
                        run_id=active_run.id
                    )
                
                # Если так и не завершился - отменяем
                if active_run.status in ['queued', 'in_progress', 'cancelling']:
                    try:
                        await asyncio.to_thread(
                            client.beta.threads.runs.cancel,
                            thread_id=thread_id,
                            run_id=active_run.id
                        )
                        await asyncio.sleep(1)
                    except:
                        pass
            
            # Добавляем сообщение в thread
            await asyncio.to_thread(
                client.beta.threads.messages.create,
                thread_id=thread_id,
                role="user",
                content=message
            )
            
            # Запускаем ассистента
            run = await asyncio.to_thread(
                client.beta.threads.runs.create,
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )
            
            # Ждем завершения с timeout
            wait_time = 0
            max_wait = 60  # максимум 60 секунд
            
            while run.status in ['queued', 'in_progress', 'cancelling'] and wait_time < max_wait:
                await asyncio.sleep(2)
                wait_time += 2
                run = await asyncio.to_thread(
                    client.beta.threads.runs.retrieve,
                    thread_id=thread_id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Получаем сообщения
                messages = await asyncio.to_thread(
                    client.beta.threads.messages.list,  
                    thread_id=thread_id
                )
                
                # Возвращаем последнее сообщение ассистента
                for message in messages.data:
                    if message.role == 'assistant':
                        response_text = message.content[0].text.value
                        return response_text
                
                logger.error(f"❌ No assistant message found for user {user_id}")
            
            # Если timeout - отменяем run
            if wait_time >= max_wait:
                try:
                    await asyncio.to_thread(
                        client.beta.threads.runs.cancel,
                        thread_id=thread_id,
                        run_id=run.id
                    )
                except:
                    pass
                logger.error(f"Timeout запроса для пользователя {user_id}")
                return "🕐 Извини, милая, запрос занял слишком много времени. Попробуй еще раз с более простым вопросом ✨"
            
            # Обработка failed статуса
            if run.status == 'failed':
                if hasattr(run, 'last_error') and run.last_error:
                    error_message = str(run.last_error)
                    logger.error(f"Failed run для {user_id}: {error_message}")
                    
                    # Специальная обработка критического rate limit в failed run
                    if "Request too large" in error_message or "input or output tokens must be reduced" in error_message:
                        logger.info(f"Автоматический сброс thread для пользователя {user_id} из-за критического rate limit в failed run. Сообщение пользователя: '{message[:200]}...' (длина: {len(message)} символов)")
                        await self._reset_user_thread(user_id)
                        
                        # Даем рекомендации в зависимости от длины сообщения
                        if len(message) > 1000:
                            return "🔄 Извини, милая, твое сообщение слишком длинное для обработки. Попробуй разделить его на несколько коротких вопросов - так я смогу лучше тебе помочь! ✨"
                        else:
                            return "😔 Что-то пошло не так... Попробуй переформулировать вопрос или написать еще раз 💕"
                    
                    # Обычный rate limit в failed run
                    if "rate_limit" in error_message.lower():
                        return "🕐 Извини, милая, сейчас очень много людей пишут мне одновременно! Попробуй написать через минутку — я обязательно отвечу ✨"
                    else:
                        return "😔 Что-то пошло не так при обработке твоего сообщения. Попробуй переформулировать вопрос или написать еще раз 💕"
                else:
                    return "😔 Произошла техническая ошибка. Попробуй написать еще раз через минутку 💕"
            
            logger.error(f"Ошибка выполнения запроса для пользователя {user_id}: статус {run.status}")
            
            # Логируем детали run для диагностики  
            if hasattr(run, 'last_error') and run.last_error:
                logger.error(f"Детали ошибки для {user_id}: {run.last_error}")
            
            return None
            
        except Exception as e:
            # Специальная обработка ошибки concurrent runs
            if "while a run" in str(e) and "is active" in str(e):
                logger.warning(f"Concurrent run для пользователя {user_id}, повторим через 3 сек")
                await asyncio.sleep(3)
                # Один повтор
                return await self.send_message(user_id, thread_id, message)
            
            # Обработка rate limit exceeded
            if "rate_limit_exceeded" in str(e) or "Rate limit reached" in str(e):
                logger.warning(f"Rate limit exceeded для пользователя {user_id}")
                
                # Автоматически сбрасываем thread если rate limit критичный
                if "Request too large" in str(e) or "input or output tokens must be reduced" in str(e):
                    logger.info(f"Автоматический сброс thread для пользователя {user_id} из-за критического rate limit. Сообщение пользователя: '{message[:200]}...' (длина: {len(message)} символов)")
                    await self._reset_user_thread(user_id)
                    
                    # Даем рекомендации в зависимости от длины сообщения
                    if len(message) > 1000:
                        return "🔄 Извини, милая, твое сообщение слишком длинное для обработки. Попробуй разделить его на несколько коротких вопросов - так я смогу лучше тебе помочь! ✨"
                    else:
                        return "😔 Что-то пошло не так... Попробуй переформулировать вопрос или написать еще раз 💕"
                
                # Возвращаем специальное сообщение для обычного rate limit
                return "🕐 Извини, милая, сейчас очень много людей пишут мне одновременно! Попробуй написать через минутку — я обязательно отвечу ✨"
            
            logger.error(f"Ошибка отправки сообщения для пользователя {user_id}: {e}")
            return None
    
    async def _reset_user_thread(self, user_id: int):
        """Сбрасывает OpenAI thread пользователя"""
        try:
            from core.database import db
            db.delete_openai_thread(user_id)
            logger.info(f"Thread сброшен для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка сброса thread для пользователя {user_id}: {e}")
    
    
    async def transcribe_audio(self, user_id: int, audio_file_path: str) -> Optional[str]:
        """
        Расшифровывает аудио файл в текст через OpenAI Whisper
        
        Args:
            user_id: ID пользователя
            audio_file_path: путь к аудио файлу
            
        Returns:
            str: расшифрованный текст или None при ошибке
        """
        if not self.has_openai_access(user_id):
            return None
        
        client = self._get_client()
        if not client:
            return None
            
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = await asyncio.to_thread(
                    client.audio.transcriptions.create,
                    model="whisper-1",
                    file=audio_file,
                    language="ru"  # Указываем русский язык для лучшего качества
                )
            
            transcribed_text = transcript.text
            logger.info(f"Аудио расшифровано для пользователя {user_id}")
            
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Ошибка расшифровки аудио для пользователя {user_id}: {e}")
            return None

# Глобальный экземпляр OpenAI клиента
openai_client = OpenAIClient()