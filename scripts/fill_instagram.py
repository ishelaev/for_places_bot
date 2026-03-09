#!/usr/bin/env python3
"""
Скрипт для заполнения Instagram в Excel таблице
Обрабатывает все записи, где Instagram не заполнен
"""

import sys
import time
import random
import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime

# Добавляем путь к модулю поиска Instagram
sys.path.insert(0, str(Path(__file__).parent / "Inst"))
from find_instagram import find_instagram_via_google

# Путь к Excel файлу
EXCEL_PATH = Path("/Users/ivan/Desktop/EatSpot_Bot_git/data/places.xlsx")
CITY = "Москва"

# Путь к лог файлу
LOG_FILE = Path(__file__).parent / "fill_instagram.log"

def log_message(message: str, print_to_console: bool = True):
    """Логирует сообщение в файл и консоль"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    
    # Записываем в файл
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line)
    
    # Выводим в консоль
    if print_to_console:
        print(message)

def fill_instagram_for_places():
    """Заполняет Instagram для всех мест без Instagram"""
    
    # Очищаем старый лог файл
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    
    log_message("=" * 60)
    log_message("🔍 Скрипт заполнения Instagram в Excel таблице")
    log_message("=" * 60)
    
    # Загружаем Excel файл
    if not EXCEL_PATH.exists():
        log_message(f"❌ Файл не найден: {EXCEL_PATH}")
        return
    
    log_message(f"\n📁 Загружаю файл: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    
    # Проверяем наличие колонок
    if 'Название' not in df.columns:
        log_message("❌ В файле нет колонки 'Название'")
        return
    
    if 'instagram' not in df.columns:
        log_message("➕ Добавляю колонку 'instagram'")
        df['instagram'] = None
    
    # Находим записи без Instagram
    mask = (
        df['instagram'].isna() | 
        (df['instagram'].astype(str).str.strip() == '') | 
        (df['instagram'].astype(str).str.strip().str.lower() == 'nan')
    )
    
    places_without_instagram = df[mask].copy()
    total_count = len(places_without_instagram)
    
    if total_count == 0:
        log_message("\n✅ Все записи уже имеют Instagram!")
        return
    
    log_message(f"\n📊 Найдено записей без Instagram: {total_count}")
    log_message("=" * 60)
    
    # Обрабатываем каждую запись
    found_count = 0
    not_found_count = 0
    error_count = 0
    
    for idx, row in places_without_instagram.iterrows():
        name = str(row.get('Название', '')).strip()
        categories = str(row.get('Категории', '')).strip() if pd.notna(row.get('Категории')) else ''
        
        if not name or name == 'nan' or name == '':
            log_message(f"\n⏭️  Пропускаю запись {idx}: нет названия")
            continue
        
        log_message(f"\n[{idx + 1}/{total_count}] 🔍 Ищу Instagram для: {name}")
        if categories:
            log_message(f"   Категории: {categories}")
        
        try:
            # Ищем Instagram с повторными попытками
            instagram_url = None
            max_retries = 3
            
            for attempt in range(1, max_retries + 1):
                try:
                    instagram_url = find_instagram_via_google(name, CITY, categories, verbose=False)
                    break  # Успешно нашли
                except Exception as search_error:
                    if attempt < max_retries:
                        wait_time = random.uniform(5, 10) * attempt  # Увеличиваем задержку с каждой попыткой
                        print(f"   ⚠️  Попытка {attempt}/{max_retries} не удалась, жду {wait_time:.1f} сек...")
                        time.sleep(wait_time)
                    else:
                        print(f"   ❌ Все попытки исчерпаны: {search_error}")
                        raise
            
            if instagram_url:
                # Обновляем в DataFrame
                df.at[idx, 'instagram'] = instagram_url
                found_count += 1
                log_message(f"   ✅ Найден: {instagram_url}")
            else:
                not_found_count += 1
                log_message(f"   ❌ Не найден")
            
            # Сохраняем после каждой записи (на случай прерывания)
            df.to_excel(EXCEL_PATH, index=False)
            log_message(f"   💾 Сохранено в Excel")
            
            # Прогресс
            progress = ((idx + 1) / total_count) * 100
            log_message(f"   📊 Прогресс: {progress:.1f}% ({found_count} найдено, {not_found_count} не найдено, {error_count} ошибок)")
            
            # Случайная задержка между запросами (3-7 секунд) для обхода блокировок
            wait_time = random.uniform(3, 7)
            time.sleep(wait_time)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Прервано пользователем")
            raise
        except Exception as e:
            error_count += 1
            error_msg = str(e)
            
            # Проверяем на блокировку/капчу
            if 'captcha' in error_msg.lower() or 'blocked' in error_msg.lower() or 'unusual traffic' in error_msg.lower():
                print(f"   🚫 Обнаружена блокировка Google!")
                print(f"   💡 Рекомендуется сделать паузу 10-15 минут перед продолжением")
                
                # Спрашиваем, продолжать ли
                log_message(f"   🚫 Блокировка обнаружена! Рекомендуется пауза 10-15 минут")
                log_message(f"   ⏸️  Скрипт приостановлен. Проверьте логи: {LOG_FILE}")
                # Долгая пауза перед продолжением
                wait_time = random.uniform(300, 600)  # 5-10 минут
                log_message(f"   ⏳ Автоматическое продолжение через {wait_time/60:.1f} минут...")
                time.sleep(wait_time)
                log_message(f"   ▶️  Продолжаю работу...")
            else:
                log_message(f"   ⚠️  Ошибка: {e}")
                import traceback
                error_trace = traceback.format_exc()
                log_message(f"   Детали ошибки:\n{error_trace}", print_to_console=False)
            
            # Задержка после ошибки
            time.sleep(random.uniform(5, 10))
            continue
    
    # Финальное сохранение
    df.to_excel(EXCEL_PATH, index=False)
    
    # Итоговая статистика
    log_message("\n" + "=" * 60)
    log_message("📊 ИТОГОВАЯ СТАТИСТИКА:")
    log_message("=" * 60)
    log_message(f"✅ Найдено Instagram: {found_count}")
    log_message(f"❌ Не найдено: {not_found_count}")
    log_message(f"⚠️  Ошибок: {error_count}")
    log_message(f"📁 Всего обработано: {found_count + not_found_count + error_count}")
    log_message(f"\n💾 Файл сохранен: {EXCEL_PATH}")
    log_message(f"📝 Лог файл: {LOG_FILE}")
    log_message("=" * 60)


if __name__ == "__main__":
    try:
        fill_instagram_for_places()
    except KeyboardInterrupt:
        log_message("\n\n⚠️  Прервано пользователем")
        log_message("💾 Изменения сохранены до момента прерывания")
    except Exception as e:
        log_message(f"\n❌ Критическая ошибка: {e}")
        import traceback
        error_trace = traceback.format_exc()
        log_message(f"Детали ошибки:\n{error_trace}", print_to_console=False)

