# excel_updater.py
import pandas as pd
from pathlib import Path
from yandex_parser import parse_yandex

EXCEL_PATH = Path("/Users/ivan/Desktop/EatSpot_Bot_git/data/places.xlsx")

def update_excel_with_yandex_data(url: str) -> dict:
    """
    Парсим данные с Яндекс.Карт по ссылке и обновляем соответствующую строку в places.xlsx.
    Если строки с такой ссылкой нет, создаём новую.
    Возвращает словарь с данными для отображения пользователю.
    """
    # Парсим данные
    data = parse_yandex(url)

    # Загружаем Excel
    df = pd.read_excel(EXCEL_PATH)

    # Проверяем наличие ссылки
    if url in df['Ссылка'].values:
        row_idx = df[df['Ссылка'] == url].index[0]
    else:
        # Создаем новую строку с пустыми значениями
        row_idx = len(df)
        df.loc[row_idx] = [None]*len(df.columns)
        df.at[row_idx, 'Ссылка'] = url

    # Обновляем колонки
    df.at[row_idx, 'Название'] = data['title']
    df.at[row_idx, 'Рейтинг'] = data['rating']
    df.at[row_idx, 'Отзывы'] = data['reviews']
    df.at[row_idx, 'Категории'] = data.get('categories')

    latitude = longitude = None
    if data['coordinates']:
        latitude, longitude = data['coordinates']  # распаковали кортеж
        df.at[row_idx, 'Широта'] = latitude
        df.at[row_idx, 'Долгота'] = longitude


    for day, hours in data['hours'].items():
        if day in df.columns:
            df.at[row_idx, day] = hours

    # Сохраняем Excel обратно
    df.to_excel(EXCEL_PATH, index=False)

    return data
