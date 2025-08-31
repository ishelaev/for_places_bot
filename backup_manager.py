#!/usr/bin/env python3
"""
Backup Manager - автоматическое резервное копирование данных
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import json
import os

class BackupManager:
    def __init__(self, backup_dir: str = "backups"):
        """Инициализация менеджера резервных копий"""
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Создаем подпапки
        (self.backup_dir / "excel").mkdir(exist_ok=True)
        (self.backup_dir / "json").mkdir(exist_ok=True)
        (self.backup_dir / "csv").mkdir(exist_ok=True)
    
    def create_excel_backup(self, data: list, filename: str = None) -> str:
        """Создает резервную копию в Excel формате"""
        try:
            if not data:
                print("⚠️ Нет данных для резервного копирования")
                return None
            
            # Создаем DataFrame
            df = pd.DataFrame(data)
            
            # Генерируем имя файла с датой
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"places_backup_{timestamp}.xlsx"
            
            filepath = self.backup_dir / "excel" / filename
            
            # Сохраняем в Excel
            df.to_excel(filepath, index=False)
            print(f"✅ Excel резервная копия создана: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Ошибка создания Excel резервной копии: {e}")
            return None
    
    def create_json_backup(self, data: list, filename: str = None) -> str:
        """Создает резервную копию в JSON формате"""
        try:
            if not data:
                print("⚠️ Нет данных для резервного копирования")
                return None
            
            # Генерируем имя файла с датой
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"places_backup_{timestamp}.json"
            
            filepath = self.backup_dir / "json" / filename
            
            # Сохраняем в JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON резервная копия создана: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Ошибка создания JSON резервной копии: {e}")
            return None
    
    def create_csv_backup(self, data: list, filename: str = None) -> str:
        """Создает резервную копию в CSV формате"""
        try:
            if not data:
                print("⚠️ Нет данных для резервного копирования")
                return None
            
            # Создаем DataFrame
            df = pd.DataFrame(data)
            
            # Генерируем имя файла с датой
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"places_backup_{timestamp}.csv"
            
            filepath = self.backup_dir / "csv" / filename
            
            # Сохраняем в CSV
            df.to_csv(filepath, index=False, encoding='utf-8')
            print(f"✅ CSV резервная копия создана: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Ошибка создания CSV резервной копии: {e}")
            return None
    
    def create_full_backup(self, data: list) -> dict:
        """Создает полную резервную копию во всех форматах"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        results = {
            'timestamp': timestamp,
            'excel': None,
            'json': None,
            'csv': None
        }
        
        # Создаем резервные копии во всех форматах
        results['excel'] = self.create_excel_backup(data, f"places_backup_{timestamp}.xlsx")
        results['json'] = self.create_json_backup(data, f"places_backup_{timestamp}.json")
        results['csv'] = self.create_csv_backup(data, f"places_backup_{timestamp}.csv")
        
        print(f"🔄 Полная резервная копия создана: {timestamp}")
        return results
    
    def cleanup_old_backups(self, keep_days: int = 30):
        """Удаляет старые резервные копии (старше указанного количества дней)"""
        try:
            cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
            
            for format_dir in ['excel', 'json', 'csv']:
                format_path = self.backup_dir / format_dir
                if format_path.exists():
                    for file in format_path.iterdir():
                        if file.is_file():
                            if file.stat().st_mtime < cutoff_date:
                                file.unlink()
                                print(f"🗑️ Удален старый файл: {file}")
            
            print(f"🧹 Очистка завершена (оставлены файлы за последние {keep_days} дней)")
            
        except Exception as e:
            print(f"❌ Ошибка очистки старых резервных копий: {e}")
    
    def get_backup_stats(self) -> dict:
        """Возвращает статистику резервных копий"""
        stats = {
            'total_files': 0,
            'excel_files': 0,
            'json_files': 0,
            'csv_files': 0,
            'total_size_mb': 0
        }
        
        try:
            for format_dir in ['excel', 'json', 'csv']:
                format_path = self.backup_dir / format_dir
                if format_path.exists():
                    files = list(format_path.iterdir())
                    stats[f'{format_dir}_files'] = len(files)
                    stats['total_files'] += len(files)
                    
                    for file in files:
                        if file.is_file():
                            stats['total_size_mb'] += file.stat().st_size / (1024 * 1024)
            
            stats['total_size_mb'] = round(stats['total_size_mb'], 2)
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
        
        return stats

# Пример использования
if __name__ == "__main__":
    backup_manager = BackupManager()
    
    # Пример данных
    sample_data = [
        {
            'Ссылка': 'https://example.com',
            'Название': 'Тестовое место',
            'Рейтинг': '4.5',
            'Отзывы': '100 отзывов'
        }
    ]
    
    # Создаем резервную копию
    backup_manager.create_full_backup(sample_data)
    
    # Показываем статистику
    stats = backup_manager.get_backup_stats()
    print(f"📊 Статистика резервных копий: {stats}")
