import sqlite3
import asyncio
from datetime import datetime
from typing import Optional

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
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    
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
        print(f"💾 Автоспам отмечен как завершенный для пользователя {user_id}")
    
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
        print(f"🔄 Статус автоспама сброшен для пользователя {user_id}")
    
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
        print(f"💾 UTM метки сохранены в БД для пользователя {user_id}")
    
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

# Глобальный экземпляр базы данных
db = Database()