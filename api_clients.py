import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import numpy as np

class AvitoAPIClient:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.avito.ru"
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_apartment_prices(self, region, rooms, period_months=24):
        """
        Получение данных о ценах на квартиры
        """
        try:
            # Увеличиваем минимальный период данных для лучшего обучения
            min_period = max(period_months, 12)  # Минимум 12 месяцев
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=min_period*30)
            
            dates = pd.date_range(start=start_date, end=end_date, freq='ME')
            
            # Базовые цены для регионов
            base_prices = {
                'Москва': 8000000,
                'Санкт-Петербург': 6000000,
                'Новосибирск': 4000000,
                'Екатеринбург': 4500000,
                'Казань': 4200000
            }
            
            base_price = base_prices.get(region, 4000000)
            
            # Модификатор для количества комнат
            room_modifiers = {'1': 0.9, '2': 1.0, '3': 1.2, '4+': 1.5}
            room_mod = room_modifiers.get(rooms, 1.0)
            base_price *= room_mod
            
            # Генерация более реалистичных данных
            trend = np.linspace(0, base_price * 0.2, len(dates))  # 20% рост за весь период
            seasonality = base_price * 0.05 * np.sin(np.linspace(0, 4*np.pi, len(dates)))
            noise = np.random.normal(0, base_price * 0.02, len(dates))  # 2% шум
            
            prices = base_price + trend + seasonality + noise
            
            data = pd.DataFrame({
                'date': dates,
                'price': prices.astype(int),
                'region': region,
                'rooms': rooms
            })
            
            return data
            
        except Exception as e:
            st.error(f"Ошибка при получении данных из Avito API: {e}")
            return None

class HHAPIClient:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.hh.ru"
    
    def get_salary_data(self, programming_language, period_months=24):
        """
        Получение данных о зарплатах по языкам программирования
        """
        try:
            # Увеличиваем минимальный период данных
            min_period = max(period_months, 12)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=min_period*30)
            
            dates = pd.date_range(start=start_date, end=end_date, freq='ME')
            
            # Базовые зарплаты для разных языков (в рублях)
            base_salaries = {
                'python': 120000,
                'java': 130000,
                'c#': 110000,
                'javascript': 115000,
                'golang': 140000,
                'rust': 150000
            }
            
            base_salary = base_salaries.get(programming_language.lower(), 100000)
            
            # Генерация более реалистичных данных
            trend = np.linspace(0, base_salary * 0.15, len(dates))  # 15% рост
            seasonality = base_salary * 0.03 * np.sin(np.linspace(0, 4*np.pi, len(dates)))
            noise = np.random.normal(0, base_salary * 0.02, len(dates))
            
            salaries = base_salary + trend + seasonality + noise
            
            data = pd.DataFrame({
                'date': dates,
                'salary': salaries.astype(int),
                'language': programming_language
            })
            
            return data
            
        except Exception as e:
            st.error(f"Ошибка при получении данных из HH API: {e}")
            return None

def get_available_regions():
    """Список доступных регионов"""
    return ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань']

def get_available_languages():
    """Список доступных языков программирования"""
    return ['Python', 'Java', 'C#', 'JavaScript', 'Golang', 'Rust']