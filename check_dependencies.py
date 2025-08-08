#!/usr/bin/env python3
"""
Скрипт для проверки совместимости зависимостей
"""
import sys
import importlib
import platform

def check_dependencies():
    print(f"Python версия: {sys.version}")
    print(f"Платформа: {platform.system()} {platform.release()}")
    print("-" * 50)
    
    dependencies = [
        ('aiogram', '3.7.0'),
        ('openai', '1.54.4'),
        ('flask', '3.0.0'),
        ('requests', '2.31.0'),
        ('aiohttp', '3.9.5'),
        ('dotenv', '1.0.1'),
    ]
    
    all_ok = True
    
    for module_name, expected_version in dependencies:
        try:
            if module_name == 'dotenv':
                import python_dotenv
                module = python_dotenv
                module_name = 'python-dotenv'
            else:
                module = importlib.import_module(module_name)
            
            version = getattr(module, '__version__', 'неизвестно')
            
            status = "✅" if version == expected_version else "⚠️"
            print(f"{status} {module_name}: {version} (ожидается: {expected_version})")
            
            if version != expected_version:
                all_ok = False
                
        except ImportError as e:
            print(f"❌ {module_name}: НЕ УСТАНОВЛЕН")
            all_ok = False
    
    print("-" * 50)
    
    # Проверяем OpenAI клиент
    try:
        import openai
        print(f"Тест OpenAI клиента...")
        
        # Пробуем создать клиент с минимальными параметрами
        try:
            client = openai.OpenAI(api_key="test_key", timeout=30.0)
            print("✅ OpenAI клиент создается без ошибок (с timeout)")
        except TypeError:
            # Если timeout не поддерживается, пробуем без него
            client = openai.OpenAI(api_key="test_key")
            print("✅ OpenAI клиент создается без ошибок (без timeout)")
        
    except Exception as e:
        print(f"❌ Ошибка создания OpenAI клиента: {e}")
        all_ok = False
    
    if all_ok:
        print("✅ Все зависимости в порядке!")
    else:
        print("⚠️ Обнаружены проблемы с зависимостями")
        print("Выполните: pip install -r requirements-lock.txt --upgrade")
    
    return all_ok

if __name__ == "__main__":
    check_dependencies()