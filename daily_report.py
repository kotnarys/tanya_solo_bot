#!/usr/bin/env python3
"""
Генератор суточного отчета по трафику
Запускать: python3 daily_report.py
"""

import sys
import os
from datetime import datetime
from core.database import db

def main():
    print("📊 ГЕНЕРАЦИЯ СУТОЧНОГО ОТЧЕТА")
    print("=" * 50)
    
    try:
        # Генерируем отчет
        report = db.get_daily_report()
        
        # Выводим в консоль
        print(report)
        
        # Сохраняем в файл
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"traffic_report_{today}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n✅ Отчет сохранен в файл: {filename}")
        
    except Exception as e:
        print(f"❌ Ошибка генерации отчета: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()