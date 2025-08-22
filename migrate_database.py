#!/usr/bin/env python3
"""
Скрипт миграции базы данных для добавления таблиц file_id и заблокированных пользователей
Запустить на сервере: python3 migrate_database.py
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Добавляет новые таблицы в базу данных"""
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    try:
        # 1. Таблица для хранения file_id медиафайлов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_file_ids (
                file_path TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("✅ Таблица media_file_ids создана")
        
        # 2. Таблица для заблокированных пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id INTEGER PRIMARY KEY,
                blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        ''')
        logger.info("✅ Таблица blocked_users создана")
        
        # 3. Таблица для мониторинга трафика
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                operation TEXT NOT NULL,
                user_id INTEGER,
                data_type TEXT,
                data_size INTEGER,
                file_path TEXT,
                status TEXT,
                error_message TEXT
            )
        ''')
        logger.info("✅ Таблица traffic_log создана")
        
        # 4. Таблица для суточной статистики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                total_messages INTEGER DEFAULT 0,
                total_media_sent INTEGER DEFAULT 0,
                total_bytes_sent INTEGER DEFAULT 0,
                openai_requests INTEGER DEFAULT 0,
                openai_bytes INTEGER DEFAULT 0,
                blocked_users_count INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0
            )
        ''')
        logger.info("✅ Таблица daily_stats создана")
        
        # Создаем индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_traffic_timestamp ON traffic_log(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_traffic_user ON traffic_log(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_file_id ON media_file_ids(file_id)')
        
        conn.commit()
        logger.info("✅ Все миграции успешно применены")
        
        # Показываем текущие таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"📊 Текущие таблицы в БД: {[t[0] for t in tables]}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
    print("\n✅ Миграция завершена! Теперь запустите бота с новым кодом.")