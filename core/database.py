import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Путь к базе данных
DB_PATH = "bot_database.db"

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица для отслеживания автоспама
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_spam_history (
                user_id INTEGER PRIMARY KEY,
                spam_completed BOOLEAN DEFAULT FALSE,
                spam_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для UTM меток (на будущее)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_utm (
                user_id INTEGER PRIMARY KEY,
                utm_source TEXT,
                utm_medium TEXT,
                utm_campaign TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для отслеживания подписок (только текущая активная)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                user_id INTEGER PRIMARY KEY,
                tariff_type TEXT NOT NULL,
                payment_date TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                payment_id TEXT,
                basic_count INTEGER DEFAULT 0,
                vip_count INTEGER DEFAULT 0,
                course_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для OpenAI threads
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS openai_threads (
                user_id INTEGER PRIMARY KEY,
                thread_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_reset_date DATE DEFAULT (date('now'))
            )
        ''')
        
        # Таблица для отслеживания отправленных купи-видео
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kupi_video_sent (
                user_id INTEGER PRIMARY KEY,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                video_path TEXT
            )
        ''')
        
        # Таблицы для реферальной системы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_users (
                user_id INTEGER PRIMARY KEY,
                email TEXT,
                referrer_user_id INTEGER,
                referral_balance INTEGER DEFAULT 0,
                waiting_for_referrer BOOLEAN DEFAULT FALSE,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_user_id) REFERENCES referral_users (user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_user_id INTEGER,
                referred_user_id INTEGER,
                bonus_amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_user_id) REFERENCES referral_users (user_id),
                FOREIGN KEY (referred_user_id) REFERENCES referral_users (user_id)
            )
        ''')
        
        # Таблица для логов рассылок новостей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                audience_type TEXT NOT NULL,
                message_text TEXT,
                media_type TEXT DEFAULT 'text',
                total_recipients INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        
        # Добавляем недостающие колонки если их нет
        try:
            cursor.execute("ALTER TABLE user_subscriptions ADD COLUMN basic_count INTEGER DEFAULT 0")
            logger.info("Добавлена колонка basic_count")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
            
        try:
            cursor.execute("ALTER TABLE user_subscriptions ADD COLUMN vip_count INTEGER DEFAULT 0")
            logger.info("Добавлена колонка vip_count")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
            
        try:
            cursor.execute("ALTER TABLE user_subscriptions ADD COLUMN course_count INTEGER DEFAULT 0")
            logger.info("Добавлена колонка course_count")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
            
        try:
            cursor.execute("ALTER TABLE openai_threads ADD COLUMN last_reset_date DATE DEFAULT (date('now'))")
            logger.info("Добавлена колонка last_reset_date в openai_threads")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")

    def is_spam_completed(self, user_id: int) -> bool:
        """
        Проверяет, был ли уже отправлен автоспам пользователю
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если спам уже был отправлен
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT spam_completed FROM auto_spam_history WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return bool(result[0])
        return False
    
    def mark_spam_completed(self, user_id: int):
        """
        Отмечает, что автоспам для пользователя завершен
        
        Args:
            user_id: ID пользователя
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO auto_spam_history 
            (user_id, spam_completed, spam_date)
            VALUES (?, ?, ?)
        ''', (user_id, True, current_time))
        
        conn.commit()
        conn.close()
        logger.info(f"Автоспам отмечен как завершенный для пользователя {user_id}")
    
    def reset_spam_status(self, user_id: int):
        """
        Сбрасывает статус автоспама для пользователя (для тестирования)
        
        Args:
            user_id: ID пользователя
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE auto_spam_history SET spam_completed = FALSE WHERE user_id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Статус автоспама сброшен для пользователя {user_id}")
    
    def get_spam_stats(self) -> dict:
        """
        Получает статистику по автоспаму
        
        Returns:
            dict: статистика
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общее количество пользователей, получивших спам
        cursor.execute("SELECT COUNT(*) FROM auto_spam_history WHERE spam_completed = TRUE")
        completed_count = cursor.fetchone()[0]
        
        # Общее количество пользователей в базе
        cursor.execute("SELECT COUNT(*) FROM auto_spam_history")
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "spam_completed": completed_count,
            "total_users": total_count,
            "spam_pending": total_count - completed_count
        }
    
    def save_user_utm(self, user_id: int, utm_data: dict):
        """
        Сохраняет UTM метки пользователя в базу данных
        
        Args:
            user_id: ID пользователя
            utm_data: словарь с UTM метками
        """
        if not utm_data:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_utm 
            (user_id, utm_source, utm_medium, utm_campaign, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,
            utm_data.get('utm_source', ''),
            utm_data.get('utm_medium', ''),
            utm_data.get('utm_campaign', ''),
            current_time
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"UTM метки сохранены в БД для пользователя {user_id}")
    
    def get_user_utm(self, user_id: int) -> dict:
        """
        Получает UTM метки пользователя из базы данных
        
        Args:
            user_id: ID пользователя
            
        Returns:
            dict: UTM метки
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT utm_source, utm_medium, utm_campaign FROM user_utm WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'utm_source': result[0] or '',
                'utm_medium': result[1] or '',
                'utm_campaign': result[2] or ''
            }
        return {}
    
    def save_subscription(self, user_id: int, tariff_type: str, payment_id: str):
        """
        Сохраняет подписку пользователя на 30 дней и увеличивает счетчик покупок.
        Если у пользователя уже есть активная подписка, продлевает её, а не перезаписывает.
        
        Args:
            user_id: ID пользователя
            tariff_type: тип тарифа (basic/vip/course)
            payment_id: ID платежа
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        payment_date = datetime.now()
        
        # Проверяем, есть ли у пользователя активная подписка
        current_subscription = self.get_user_subscription(user_id)
        
        if current_subscription and current_subscription.get('is_active', False):
            # Если есть активная подписка, продлеваем с момента её окончания
            current_expires = datetime.fromisoformat(current_subscription['expires_at'])
            # Продлеваем с момента окончания текущей подписки или с текущего момента (если подписка уже истекла)
            start_date = max(current_expires, payment_date)
            expires_at = start_date + timedelta(days=30)
            logger.info(f"Продление существующей подписки для пользователя {user_id}: с {start_date.strftime('%d.%m.%Y %H:%M')} до {expires_at.strftime('%d.%m.%Y %H:%M')}")
        else:
            # Если нет активной подписки, начинаем с текущего момента
            expires_at = payment_date + timedelta(days=30)
            logger.info(f"Новая подписка для пользователя {user_id}: с {payment_date.strftime('%d.%m.%Y %H:%M')} до {expires_at.strftime('%d.%m.%Y %H:%M')}")
        
        # Получаем текущие счетчики или инициализируем нулями для нового пользователя
        cursor.execute("SELECT basic_count, vip_count, course_count FROM user_subscriptions WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result:
            # Пользователь уже существует - увеличиваем соответствующий счетчик
            basic_count, vip_count, course_count = result
            if tariff_type == "basic":
                basic_count += 1
            elif tariff_type == "vip":
                vip_count += 1
            elif tariff_type == "course":
                course_count += 1
            logger.info(f"Продление подписки для пользователя {user_id}, увеличиваем счетчик {tariff_type}")
        else:
            # Новый пользователь - устанавливаем счетчик в 1 для купленного тарифа
            basic_count = 1 if tariff_type == "basic" else 0
            vip_count = 1 if tariff_type == "vip" else 0
            course_count = 1 if tariff_type == "course" else 0
            logger.info(f"Создаем новую подписку для пользователя {user_id}")
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_subscriptions 
            (user_id, tariff_type, payment_date, expires_at, is_active, payment_id, basic_count, vip_count, course_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            tariff_type,
            payment_date.isoformat(),
            expires_at.isoformat(),
            True,
            payment_id,
            basic_count,
            vip_count,
            course_count
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Подписка сохранена для пользователя {user_id}, тариф {tariff_type}, до {expires_at.strftime('%d.%m.%Y %H:%M')}")
        logger.info(f"Счетчики: basic={basic_count}, vip={vip_count}, course={course_count}")
    
    def get_user_subscription(self, user_id: int) -> dict:
        """
        Получает информацию о подписке пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            dict: информация о подписке или пустой словарь
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tariff_type, payment_date, expires_at, is_active, payment_id, basic_count, vip_count, course_count
            FROM user_subscriptions 
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            expires_at = datetime.fromisoformat(result[2])
            is_expired = datetime.now() > expires_at
            
            return {
                'tariff_type': result[0],
                'payment_date': result[1],
                'expires_at': result[2],
                'is_active': result[3] and not is_expired,
                'is_expired': is_expired,
                'payment_id': result[4],
                'basic_count': result[5] or 0,
                'vip_count': result[6] or 0,
                'course_count': result[7] or 0,
                'days_left': max(0, (expires_at - datetime.now()).days)
            }
        return {}
    
    def is_user_subscribed(self, user_id: int) -> bool:
        """
        Проверяет, есть ли у пользователя активная подписка или вечный доступ
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если есть активная подписка или вечный доступ
        """
        from core.config import PERMANENT_ACCESS_IDS
        
        # Проверяем вечный доступ для администраторов
        if user_id in PERMANENT_ACCESS_IDS:
            return True
            
        # Проверяем обычную подписку
        subscription = self.get_user_subscription(user_id)
        return subscription.get('is_active', False)
    
    def get_earliest_subscription_expiry(self):
        """
        Получает самую раннюю дату окончания активной подписки
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            current_time = datetime.now().isoformat()
            
            # Находим минимальную дату окончания среди активных подписок
            cursor.execute('''
                SELECT MIN(expires_at), user_id
                FROM user_subscriptions 
                WHERE expires_at > ? AND is_active = TRUE
            ''', (current_time,))
            
            result = cursor.fetchone()
            
            if result and result[0]:
                expires_at = datetime.fromisoformat(result[0])
                user_id = result[1]
                days_left = (expires_at - datetime.now()).days
                
                # Получаем детали о всех подписках, которые заканчиваются в ближайшие дни
                cursor.execute('''
                    SELECT user_id, tariff_type, expires_at
                    FROM user_subscriptions 
                    WHERE expires_at > ? AND is_active = TRUE
                    ORDER BY expires_at ASC
                    LIMIT 10
                ''', (current_time,))
                
                upcoming_expirations = []
                for row in cursor.fetchall():
                    exp_date = datetime.fromisoformat(row[2])
                    upcoming_expirations.append({
                        'user_id': row[0],
                        'tariff': row[1],
                        'expires_at': exp_date.strftime('%Y-%m-%d %H:%M'),
                        'days_left': (exp_date - datetime.now()).days
                    })
                
                return {
                    'earliest_expiry': expires_at.strftime('%Y-%m-%d %H:%M'),
                    'earliest_user_id': user_id,
                    'days_until_expiry': days_left,
                    'upcoming_10': upcoming_expirations
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения даты окончания подписок: {e}")
            return None
        finally:
            conn.close()
    
    def get_subscription_stats(self) -> dict:
        """
        Получает статистику по подпискам
        
        Returns:
            dict: статистика
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Всего подписок
        cursor.execute("SELECT COUNT(*) FROM user_subscriptions")
        total_subscriptions = cursor.fetchone()[0]
        
        # Активные подписки (не истекшие)
        current_time = datetime.now().isoformat()
        cursor.execute(
            "SELECT COUNT(*) FROM user_subscriptions WHERE expires_at > ? AND is_active = TRUE",
            (current_time,)
        )
        active_subscriptions = cursor.fetchone()[0]
        
        # По тарифам
        cursor.execute(
            "SELECT tariff_type, COUNT(*) FROM user_subscriptions WHERE expires_at > ? AND is_active = TRUE GROUP BY tariff_type",
            (current_time,)
        )
        tariff_stats = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'expired_subscriptions': total_subscriptions - active_subscriptions,
            'basic_active': tariff_stats.get('basic', 0),
            'vip_active': tariff_stats.get('vip', 0)
        }
    
    def fix_missing_subscription(self, user_id: int, tariff_type: str):
        """
        Быстрая функция для исправления пропущенных подписок
        """
        payment_id = f"fix_{user_id}_{tariff_type}_{int(datetime.now().timestamp())}"
        self.save_subscription(user_id, tariff_type, payment_id)
        print(f"🔧 Исправлена подписка: user_id={user_id}, тариф={tariff_type}")
    
    def save_openai_thread(self, user_id: int, thread_id: str):
        """
        Сохраняет OpenAI thread для пользователя
        
        Args:
            user_id: ID пользователя
            thread_id: ID thread в OpenAI
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT OR REPLACE INTO openai_threads 
            (user_id, thread_id, updated_at, last_reset_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, thread_id, current_time, current_date))
        
        conn.commit()
        conn.close()
        logger.info(f"OpenAI thread сохранен для пользователя {user_id}: {thread_id}")
    
    def get_openai_thread(self, user_id: int) -> Optional[dict]:
        """
        Получает OpenAI thread пользователя с датой последнего сброса
        
        Args:
            user_id: ID пользователя
            
        Returns:
            dict: {'thread_id': str, 'last_reset_date': str} или None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT thread_id, last_reset_date FROM openai_threads WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'thread_id': result[0],
                'last_reset_date': result[1] or datetime.now().strftime('%Y-%m-%d')
            }
        return None
    
    def is_kupi_video_sent(self, user_id: int) -> bool:
        """
        Проверяет, было ли уже отправлено купи-видео пользователю
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если видео уже было отправлено
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM kupi_video_sent WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def mark_kupi_video_sent(self, user_id: int, video_path: str):
        """
        Отмечает, что купи-видео отправлено пользователю
        
        Args:
            user_id: ID пользователя
            video_path: путь к отправленному видео
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO kupi_video_sent 
            (user_id, sent_at, video_path)
            VALUES (?, ?, ?)
        ''', (user_id, current_time, video_path))
        
        conn.commit()
        conn.close()
        logger.info(f"Купи-видео отмечено как отправленное для пользователя {user_id}")
    
    def get_users_for_kupi_video(self) -> list:
        """
        Получает список пользователей, которым нужно отправить купи-видео:
        - пользователи без активной подписки
        - прошло больше часа с момента их первого входа в бота
        - купи-видео еще не отправлялось
        
        Returns:
            list: список user_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем время час назад
        hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        current_time = datetime.now().isoformat()
        
        # Находим всех пользователей из auto_spam_history и user_utm, у которых:
        # 1. Дата создания больше часа назад
        # 2. Нет активной подписки
        # 3. Купи-видео еще не отправлялось
        cursor.execute('''
            WITH all_users AS (
                SELECT user_id, created_at FROM auto_spam_history
                UNION
                SELECT user_id, created_at FROM user_utm
            ),
            eligible_users AS (
                SELECT DISTINCT u.user_id
                FROM all_users u
                WHERE u.created_at < ?
                  AND u.user_id NOT IN (
                    SELECT user_id 
                    FROM user_subscriptions 
                    WHERE expires_at > ? AND is_active = TRUE
                  )
                  AND u.user_id NOT IN (
                    SELECT user_id FROM kupi_video_sent
                  )
            )
            SELECT user_id FROM eligible_users
        ''', (hour_ago, current_time))
        
        results = cursor.fetchall()
        conn.close()
        
        user_ids = [result[0] for result in results]
        logger.info(f"Найдено {len(user_ids)} пользователей для отправки купи-видео")
        
        return user_ids
    
    def reset_kupi_video_history(self):
        """
        Сбрасывает историю отправки купи-видео - удаляет все записи из kupi_video_sent
        чтобы всем пользователям можно было отправить заново
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Удаляем все записи из таблицы kupi_video_sent
            cursor.execute('DELETE FROM kupi_video_sent')
            deleted_count = cursor.rowcount
            
            conn.commit()
            logger.info(f"История купи-видео сброшена. Удалено записей: {deleted_count}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка сброса истории купи-видео: {e}")
            raise
        finally:
            conn.close()
    
    def get_active_subscribers(self) -> list:
        """
        Получает список всех пользователей с активной подпиской
        
        Returns:
            list: список user_id пользователей с активной подпиской
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            SELECT user_id FROM user_subscriptions 
            WHERE expires_at > ? AND is_active = TRUE
        ''', (current_time,))
        
        results = cursor.fetchall()
        conn.close()
        
        user_ids = [result[0] for result in results]
        logger.info(f"Найдено {len(user_ids)} пользователей с активной подпиской")
        
        return user_ids
    
    # Реферальная система
    def register_referral_user(self, user_id: int, email: str, referrer_user_id: int = None):
        """Регистрирует пользователя в реферальной системе"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO referral_users 
                (user_id, email, referrer_user_id, referral_balance, registered_at)
                VALUES (?, ?, ?, 0, ?)
            ''', (user_id, email, referrer_user_id, datetime.now().isoformat()))
            
            conn.commit()
            logger.info(f"Пользователь {user_id} зарегистрирован в реферальной системе")
            
        except Exception as e:
            logger.error(f"Ошибка регистрации в реферальной системе для {user_id}: {e}")
        finally:
            conn.close()
    
    def get_referral_info(self, user_id: int):
        """Получает информацию о реферальном профиле пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT email, referrer_user_id, referral_balance, registered_at
                FROM referral_users WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'email': result[0],
                    'referrer_user_id': result[1],
                    'referral_balance': result[2],
                    'registered_at': result[3]
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения реферальной информации для {user_id}: {e}")
            return None
        finally:
            conn.close()
    
    def add_referral_bonus(self, referrer_user_id: int, referred_user_id: int, bonus_amount: int):
        """Добавляет реферальный бонус"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Добавляем запись о бонусе
            cursor.execute('''
                INSERT INTO referral_bonuses 
                (referrer_user_id, referred_user_id, bonus_amount, created_at)
                VALUES (?, ?, ?, ?)
            ''', (referrer_user_id, referred_user_id, bonus_amount, datetime.now().isoformat()))
            
            # Обновляем баланс реферера
            cursor.execute('''
                UPDATE referral_users 
                SET referral_balance = referral_balance + ?
                WHERE user_id = ?
            ''', (bonus_amount, referrer_user_id))
            
            conn.commit()
            logger.info(f"Добавлен реферальный бонус {bonus_amount} для пользователя {referrer_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления реферального бонуса: {e}")
            return False
        finally:
            conn.close()
    
    def use_referral_balance(self, user_id: int, amount: int):
        """Использует реферальный баланс"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE referral_users 
                SET referral_balance = referral_balance - ?
                WHERE user_id = ? AND referral_balance >= ?
            ''', (amount, user_id, amount))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"Использован реферальный баланс {amount} пользователем {user_id}")
                return True
            else:
                logger.warning(f"Недостаточно реферального баланса у пользователя {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка использования реферального баланса: {e}")
            return False
        finally:
            conn.close()
    
    def is_referral_user_registered(self, user_id: int):
        """Проверяет, зарегистрирован ли пользователь в реферальной системе"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT 1 FROM referral_users WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Ошибка проверки регистрации в реферальной системе: {e}")
            return False
        finally:
            conn.close()
    
    def set_waiting_for_referrer(self, user_id: int, waiting: bool):
        """Устанавливает флаг ожидания реферера"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE referral_users 
                SET waiting_for_referrer = ?
                WHERE user_id = ?
            ''', (waiting, user_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Ошибка установки флага ожидания реферера: {e}")
        finally:
            conn.close()
    
    def update_referral_user_email(self, user_id: int, email: str):
        """Обновляет email для существующего пользователя в реферальной системе"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE referral_users 
                SET email = ?
                WHERE user_id = ?
            ''', (email, user_id))
            conn.commit()
            logger.info(f"Email обновлен для пользователя {user_id}: {email}")
        except Exception as e:
            logger.error(f"Ошибка обновления email для {user_id}: {e}")
        finally:
            conn.close()
    
    def is_waiting_for_referrer(self, user_id: int):
        """Проверяет, ожидает ли пользователь ввода реферера"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT waiting_for_referrer FROM referral_users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else False
        except Exception as e:
            logger.error(f"Ошибка проверки ожидания реферера: {e}")
            return False
        finally:
            conn.close()
    
    # Функции для рассылки новостей
    def get_all_users(self) -> list:
        """Получает список всех пользователей бота"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Собираем пользователей из всех таблиц
            cursor.execute('''
                SELECT DISTINCT user_id FROM (
                    SELECT user_id FROM auto_spam_history
                    UNION
                    SELECT user_id FROM user_utm  
                    UNION
                    SELECT user_id FROM user_subscriptions
                    UNION
                    SELECT user_id FROM openai_threads
                    UNION
                    SELECT user_id FROM referral_users
                )
            ''')
            
            results = cursor.fetchall()
            user_ids = [result[0] for result in results]
            
            logger.info(f"Найдено {len(user_ids)} уникальных пользователей")
            return user_ids
            
        except Exception as e:
            logger.error(f"Ошибка получения всех пользователей: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_users_count(self) -> int:
        """Получает количество всех пользователей бота"""
        return len(self.get_all_users())
    
    def get_course_users(self) -> list:
        """Получает пользователей с подпиской course (активной или была)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT DISTINCT user_id FROM user_subscriptions 
                WHERE tariff_type = 'course' OR course_count > 0
            ''')
            
            results = cursor.fetchall()
            user_ids = [result[0] for result in results]
            
            logger.info(f"Найдено {len(user_ids)} пользователей курса")
            return user_ids
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователей курса: {e}")
            return []
        finally:
            conn.close()
    
    def get_course_users_count(self) -> int:
        """Получает количество пользователей курса"""
        return len(self.get_course_users())
    
    def get_paid_subscribers(self) -> list:
        """Получает пользователей с платными подписками (basic или vip)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT DISTINCT user_id FROM user_subscriptions 
                WHERE tariff_type IN ('basic', 'vip') 
                   OR basic_count > 0 
                   OR vip_count > 0
            ''')
            
            results = cursor.fetchall()
            user_ids = [result[0] for result in results]
            
            logger.info(f"Найдено {len(user_ids)} платных подписчиков")
            return user_ids
            
        except Exception as e:
            logger.error(f"Ошибка получения платных подписчиков: {e}")
            return []
        finally:
            conn.close()
    
    def get_paid_subscribers_count(self) -> int:
        """Получает количество платных подписчиков"""
        return len(self.get_paid_subscribers())
    
    def get_vip_users(self) -> list:
        """Получает VIP пользователей (активных или бывших)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT DISTINCT user_id FROM user_subscriptions 
                WHERE tariff_type = 'vip' OR vip_count > 0
            ''')
            
            results = cursor.fetchall()
            user_ids = [result[0] for result in results]
            
            logger.info(f"Найдено {len(user_ids)} VIP пользователей")
            return user_ids
            
        except Exception as e:
            logger.error(f"Ошибка получения VIP пользователей: {e}")
            return []
        finally:
            conn.close()
    
    def get_vip_users_count(self) -> int:
        """Получает количество VIP пользователей"""
        return len(self.get_vip_users())
    
    def create_news_broadcast(self, admin_id: int, audience_type: str, message_text: str, media_type: str, total_recipients: int) -> int:
        """Создает запись о рассылке новостей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO news_broadcasts 
                (admin_id, audience_type, message_text, media_type, total_recipients)
                VALUES (?, ?, ?, ?, ?)
            ''', (admin_id, audience_type, message_text, media_type, total_recipients))
            
            broadcast_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Создана рассылка ID {broadcast_id} от админа {admin_id}")
            return broadcast_id
            
        except Exception as e:
            logger.error(f"Ошибка создания записи рассылки: {e}")
            return 0
        finally:
            conn.close()
    
    def update_news_broadcast_stats(self, broadcast_id: int, sent_count: int, error_count: int):
        """Обновляет статистику рассылки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE news_broadcasts 
                SET sent_count = ?, error_count = ?, completed_at = ?
                WHERE id = ?
            ''', (sent_count, error_count, datetime.now().isoformat(), broadcast_id))
            
            conn.commit()
            logger.info(f"Обновлена статистика рассылки {broadcast_id}: отправлено {sent_count}, ошибок {error_count}")
            
        except Exception as e:
            logger.error(f"Ошибка обновления статистики рассылки: {e}")
        finally:
            conn.close()
    
    def get_last_reset_info(self):
        """
        Получает информацию о последнем сбросе тредов
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Получаем самую позднюю дату сброса
            cursor.execute('''
                SELECT MAX(last_reset_date), COUNT(*) 
                FROM openai_threads 
                WHERE last_reset_date IS NOT NULL
            ''')
            
            result = cursor.fetchone()
            last_reset_date = result[0] if result else None
            threads_count = result[1] if result else 0
            
            # Получаем количество тредов без даты сброса
            cursor.execute('''
                SELECT COUNT(*) FROM openai_threads 
                WHERE last_reset_date IS NULL
            ''')
            threads_without_reset = cursor.fetchone()[0]
            
            return {
                'last_reset_date': last_reset_date,
                'threads_with_reset': threads_count,
                'threads_without_reset': threads_without_reset
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о сбросе: {e}")
            return None
        finally:
            conn.close()
    
    def should_reset_thread_daily(self, user_id: int) -> bool:
        """
        Проверяет, нужно ли сбросить thread пользователя (ежедневный сброс)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если нужно сбросить thread
        """
        import pytz
        
        # Московская временная зона
        moscow_tz = pytz.timezone('Europe/Moscow')
        current_moscow_date = datetime.now(moscow_tz).strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT last_reset_date FROM openai_threads WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                # Нет записи о thread
                return False
            
            last_reset_date = result[0]
            
            # Если дата последнего сброса не сегодня по МСК, нужно сбросить
            need_reset = last_reset_date != current_moscow_date
            
            if need_reset:
                logger.info(f"Thread для пользователя {user_id} нуждается в ежедневном сбросе. Последний сброс: {last_reset_date}, сегодня: {current_moscow_date}")
            
            return need_reset
                
        except Exception as e:
            logger.error(f"Ошибка проверки ежедневного сброса для {user_id}: {e}")
            return False
        finally:
            conn.close()
    
    def delete_openai_thread(self, user_id: int):
        """
        Удаляет OpenAI thread пользователя
        
        Args:
            user_id: ID пользователя
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM openai_threads WHERE user_id = ?', (user_id,))
            conn.commit()
            logger.info(f"Thread удален для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка удаления thread для пользователя {user_id}: {e}")
        finally:
            conn.close()
    
    def delete_all_openai_threads(self):
        """
        Удаляет все OpenAI threads из базы данных
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM openai_threads')
            count_before = cursor.fetchone()[0]
            
            cursor.execute('DELETE FROM openai_threads')
            deleted_count = cursor.rowcount
            
            conn.commit()
            
            logger.info(f"Удалено {deleted_count} thread'ов из {count_before} (всего было в базе)")
            print(f"✅ Удалено {deleted_count} OpenAI thread'ов из базы данных")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка удаления всех thread'ов: {e}")
            print(f"❌ Ошибка удаления thread'ов: {e}")
            return 0
        finally:
            conn.close()
    
    def reset_all_threads_daily(self):
        """
        Ежедневный сброс всех OpenAI threads в 00:00 МСК
        """
        import pytz
        
        # Московская временная зона
        moscow_tz = pytz.timezone('Europe/Moscow')
        current_moscow_date = datetime.now(moscow_tz).strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Находим все threads, которые не сбрасывались сегодня
            cursor.execute('''
                SELECT COUNT(*) FROM openai_threads 
                WHERE last_reset_date != ? OR last_reset_date IS NULL
            ''', (current_moscow_date,))
            
            count_to_reset = cursor.fetchone()[0]
            
            if count_to_reset == 0:
                logger.info("Нет threads для ежедневного сброса")
                return 0
            
            # Удаляем все threads, которые нужно сбросить
            cursor.execute('''
                DELETE FROM openai_threads 
                WHERE last_reset_date != ? OR last_reset_date IS NULL
            ''', (current_moscow_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Ежедневный сброс: удалено {deleted_count} thread'ов")
            print(f"🔄 Ежедневный сброс: удалено {deleted_count} thread'ов ({current_moscow_date})")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка ежедневного сброса thread'ов: {e}")
            print(f"❌ Ошибка ежедневного сброса: {e}")
            return 0
        finally:
            conn.close()
    
    # ========== НОВЫЕ МЕТОДЫ ДЛЯ ОПТИМИЗАЦИИ ТРАФИКА ==========
    
    def get_media_file_id(self, file_path: str) -> Optional[str]:
        """Получает file_id для медиафайла из кэша"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT file_id FROM media_file_ids WHERE file_path = ?",
            (file_path,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def save_media_file_id(self, file_path: str, file_id: str, file_type: str, file_size: int = 0):
        """Сохраняет file_id медиафайла в кэш"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO media_file_ids 
            (file_path, file_id, file_type, file_size, last_used)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (file_path, file_id, file_type, file_size))
        
        conn.commit()
        conn.close()
        logger.info(f"File ID сохранен: {file_path} -> {file_id}")
    
    def mark_user_blocked(self, user_id: int, reason: str = "Bot blocked by user"):
        """Отмечает пользователя как заблокировавшего бота"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO blocked_users 
            (user_id, blocked_at, reason)
            VALUES (?, CURRENT_TIMESTAMP, ?)
        ''', (user_id, reason))
        
        conn.commit()
        conn.close()
        logger.info(f"Пользователь {user_id} отмечен как заблокированный: {reason}")
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Проверяет, заблокировал ли пользователь бота"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM blocked_users WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def log_traffic(self, operation: str, user_id: int = None, data_type: str = None, 
                    data_size: int = 0, file_path: str = None, status: str = "success", 
                    error_message: str = None):
        """Логирует трафик и операции для мониторинга"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO traffic_log 
            (operation, user_id, data_type, data_size, file_path, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (operation, user_id, data_type, data_size, file_path, status, error_message))
        
        conn.commit()
        conn.close()
    
    def update_daily_stats(self, **kwargs):
        """Обновляет суточную статистику"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Создаем запись на сегодня если ее нет
        cursor.execute('''
            INSERT OR IGNORE INTO daily_stats (date) VALUES (?)
        ''', (today,))
        
        # Обновляем переданные поля
        for field, value in kwargs.items():
            if field in ['total_messages', 'total_media_sent', 'total_bytes_sent', 
                        'openai_requests', 'openai_bytes', 'blocked_users_count', 
                        'new_users', 'active_users']:
                cursor.execute(f'''
                    UPDATE daily_stats 
                    SET {field} = {field} + ?
                    WHERE date = ?
                ''', (value, today))
        
        conn.commit()
        conn.close()
    
    def get_daily_report(self) -> str:
        """Генерирует суточный отчет по трафику"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Получаем статистику за сегодня
        cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (today,))
        today_stats = cursor.fetchone()
        
        # Получаем статистику за вчера для сравнения
        cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (yesterday,))
        yesterday_stats = cursor.fetchone()
        
        # Получаем топ операций по трафику
        cursor.execute('''
            SELECT operation, COUNT(*) as count, SUM(data_size) as total_size
            FROM traffic_log
            WHERE DATE(timestamp) = ?
            GROUP BY operation
            ORDER BY total_size DESC
            LIMIT 5
        ''', (today,))
        top_operations = cursor.fetchall()
        
        conn.close()
        
        # Формируем отчет
        report = f"📊 ОТЧЕТ ПО ТРАФИКУ ЗА {today}\n"
        report += "=" * 40 + "\n"
        
        if today_stats:
            report += f"📨 Сообщений отправлено: {today_stats[1] or 0}\n"
            report += f"📹 Медиафайлов отправлено: {today_stats[2] or 0}\n"
            report += f"📤 Трафик отправлен: {(today_stats[3] or 0) / 1024 / 1024:.2f} MB\n"
            report += f"🤖 OpenAI запросов: {today_stats[4] or 0}\n"
            report += f"🚫 Заблокированных пользователей: {today_stats[6] or 0}\n"
            report += f"👤 Новых пользователей: {today_stats[7] or 0}\n"
            report += f"✅ Активных пользователей: {today_stats[8] or 0}\n"
        
        if top_operations:
            report += "\n🔝 ТОП ОПЕРАЦИЙ ПО ТРАФИКУ:\n"
            for op, count, size in top_operations:
                report += f"  • {op}: {count} раз, {(size or 0) / 1024:.1f} KB\n"
        
        return report

# Глобальный экземпляр базы данных
db = Database()

def init_db():
    """Standalone функция для инициализации базы данных"""
    return db