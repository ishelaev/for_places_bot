# check_table_structure.py
from sqlalchemy import create_engine, text, inspect
from config import POSTGRES_URL

def check_table_structure():
    engine = create_engine(POSTGRES_URL)
    
    try:
        inspector = inspect(engine)
        
        if 'places' in inspector.get_table_names():
            print("✅ Таблица places существует")
            
            # Получаем информацию о колонках
            columns = inspector.get_columns('places')
            print("\n📋 Структура таблицы places:")
            for column in columns:
                print(f"  • {column['name']}: {column['type']}")
            
            # Проверяем первичный ключ
            pk = inspector.get_pk_constraint('places')
            print(f"\n🔑 Первичный ключ: {pk}")
            
            # Проверяем уникальные ограничения
            unique_constraints = inspector.get_unique_constraints('places')
            print(f"\n🔒 Уникальные ограничения: {unique_constraints}")
            
        else:
            print("❌ Таблица places не существует")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке структуры: {e}")

if __name__ == "__main__":
    check_table_structure()
