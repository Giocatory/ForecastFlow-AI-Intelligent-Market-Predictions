from autots import AutoTS
import pandas as pd
import streamlit as st
import numpy as np
import logging
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalForecastModel:
    def __init__(self, forecast_length=12, frequency='ME', model_complexity='medium'):
        """
        Универсальная модель для прогнозирования
        """
        self.forecast_length = forecast_length
        self.frequency = frequency
        self.model_complexity = model_complexity
        self.model = None
        self.best_model_name = None
        self.training_successful = False
        self.historical_data = None
        
    def prepare_data(self, data, value_column, date_column='date'):
        """Подготовка и валидация данных для AutoTS"""
        try:
            df = data.copy()
            
            # Преобразуем дату
            df[date_column] = pd.to_datetime(df[date_column])
            
            # Удаляем дубликаты дат
            df = df.drop_duplicates(subset=[date_column])
            
            # Сортируем по дате
            df = df.sort_values(date_column)
            
            # Устанавливаем дату как индекс
            df = df.set_index(date_column)
            
            # Проверяем наличие достаточного количества данных
            if len(df) < 6:
                st.warning(f"⚠️ Мало данных для обучения: {len(df)} точек. Нужно минимум 6.")
                return None
            
            # Выбираем колонку с значениями
            if value_column not in df.columns:
                st.error(f"Колонка '{value_column}' не найдена в данных")
                return None
                
            ts_data = df[[value_column]]
            
            # Сохраняем исторические данные для резервного прогноза
            self.historical_data = ts_data.copy()
            
            # Проверяем на пропуски
            if ts_data[value_column].isnull().any():
                st.warning("⚠️ В данных есть пропущенные значения. Заполняем линейной интерполяцией.")
                ts_data[value_column] = ts_data[value_column].interpolate()
            
            return ts_data
            
        except Exception as e:
            st.error(f"Ошибка подготовки данных: {str(e)}")
            return None
    
    def get_model_list(self, data_length):
        """Выбор списка моделей в зависимости от сложности и объема данных"""
        
        if self.model_complexity == 'simple':
            return 'superfast'  # Самые быстрые и стабильные модели
        
        elif self.model_complexity == 'medium':
            return 'fast'  # Быстрые модели
        
        elif self.model_complexity == 'complex':
            return 'default'  # Стандартный набор моделей
        
        else:  # 'all'
            return 'all'  # Все доступные модели
    
    def train(self, data, value_column):
        """Обучение модели с перебором всех доступных моделей"""
        try:
            # Подготовка данных
            ts_data = self.prepare_data(data, value_column)
            if ts_data is None:
                return False
            
            data_length = len(ts_data)
            
            # Выбор списка моделей
            model_list = self.get_model_list(data_length)
            
            # Настройка параметров AutoTS в зависимости от объема данных
            if data_length <= 12:
                generations = 1
                validations = 1
            elif data_length <= 24:
                generations = 2
                validations = 2
            else:
                generations = 3
                validations = 3
            
            st.info(f"""
            **Настройки обучения:**
            - Точек данных: {data_length}
            - Сложность моделей: {self.model_complexity}
            - Поколений: {generations}
            - Валидаций: {validations}
            """)
            
            # Создание и обучение модели AutoTS
            model = AutoTS(
                forecast_length=self.forecast_length,
                frequency=self.frequency,
                model_list=model_list,
                ensemble='simple',
                max_generations=generations,
                num_validations=validations,
                validation_method='backwards',
                no_negatives=True,
                constraint=2.0,
                drop_most_recent=0,
                verbose=0
            )
            
            with st.spinner("🔄 Обучение модели... Это может занять несколько минут"):
                self.model = model.fit(ts_data)
            
            # Проверка успешности обучения
            if (hasattr(self.model, 'best_model_name') and 
                self.model.best_model_name and 
                self.model.best_model_name != 'ZeroesNaive'):
                
                self.best_model_name = self.model.best_model_name
                self.training_successful = True
                
                st.success(f"✅ Модель успешно обучена! Лучшая модель: **{self.best_model_name}**")
                
                return True
            else:
                st.error("❌ Не удалось обучить подходящую модель")
                return self._train_simple_fallback(ts_data)
                
        except Exception as e:
            logger.error(f"Ошибка обучения: {str(e)}")
            st.error(f"❌ Ошибка при обучении модели: {str(e)}")
            return self._train_simple_fallback(data, value_column)
    
    def _train_simple_fallback(self, data, value_column=None):
        """Резервный метод обучения с простыми моделями"""
        try:
            st.info("🔄 Пробуем обучить упрощенную модель...")
            
            if value_column:
                ts_data = self.prepare_data(data, value_column)
            else:
                ts_data = data
            
            if ts_data is None:
                return False
            
            # Используем только самые стабильные модели
            simple_model = AutoTS(
                forecast_length=self.forecast_length,
                frequency=self.frequency,
                model_list=['LastValueNaive', 'AverageValueNaive', 'ETS', 'ARIMA'],
                ensemble=None,
                max_generations=1,
                num_validations=1,
                verbose=0
            )
            
            self.model = simple_model.fit(ts_data)
            
            if (hasattr(self.model, 'best_model_name') and 
                self.model.best_model_name):
                
                self.best_model_name = self.model.best_model_name + " (fallback)"
                self.training_successful = True
                st.success(f"✅ Упрощенная модель обучена: **{self.best_model_name}**")
                return True
            else:
                st.error("❌ Не удалось обучить даже упрощенную модель")
                return False
                
        except Exception as e:
            st.error(f"❌ Резервное обучение также не удалось: {str(e)}")
            return False
    
    def predict(self):
        """Создание прогноза"""
        if not self.training_successful or self.model is None:
            st.error("❌ Модель не обучена или обучение не было успешным")
            return self._simple_trend_forecast()
        
        try:
            with st.spinner("📊 Создание прогноза..."):
                # Пытаемся получить прогноз от обученной модели
                if hasattr(self.model, 'predict'):
                    forecast = self.model.predict()
                    if forecast is not None and hasattr(forecast, 'forecast'):
                        return forecast.forecast
                
                # Если не получилось, используем резервный метод
                st.warning("⚠️ Не удалось получить прогноз от обученной модели. Используем резервный метод.")
                return self._simple_trend_forecast()
                    
        except Exception as e:
            logger.error(f"Ошибка прогнозирования: {str(e)}")
            st.error(f"❌ Ошибка при создании прогноза: {str(e)}")
            return self._simple_trend_forecast()
    
    def _simple_trend_forecast(self):
        """Простой прогноз на основе линейного тренда"""
        try:
            if self.historical_data is None:
                st.error("❌ Нет исторических данных для создания прогноза")
                return None
            
            historical_data = self.historical_data
            values = historical_data.iloc[:, 0].values
            
            if len(values) < 2:
                # Если мало данных, используем последнее значение
                last_value = values[-1]
                forecast_values = [last_value] * self.forecast_length
            else:
                # Линейная регрессия для тренда
                x = np.arange(len(values))
                slope, intercept = np.polyfit(x, values, 1)
                
                # Создаем прогноз на основе тренда
                future_x = np.arange(len(values), len(values) + self.forecast_length)
                forecast_values = slope * future_x + intercept
            
            # Создаем даты для прогноза
            last_date = historical_data.index[-1]
            
            if self.frequency == 'D':
                dates = pd.date_range(start=last_date + timedelta(days=1), 
                                    periods=self.forecast_length, freq='D')
            elif self.frequency == 'ME':
                dates = pd.date_range(start=last_date + pd.offsets.MonthBegin(1), 
                                    periods=self.forecast_length, freq='ME')
            else:
                dates = pd.date_range(start=last_date + timedelta(days=30), 
                                    periods=self.forecast_length, freq=self.frequency)
            
            # Создаем DataFrame с прогнозом
            forecast_df = pd.DataFrame(
                forecast_values,
                index=dates,
                columns=['forecast_trend']
            )
            
            st.info("📈 Используется прогноз на основе линейного тренда")
            return forecast_df
            
        except Exception as e:
            st.error(f"❌ Простой прогноз также не сработал: {str(e)}")
            return None
    
    def get_model_info(self):
        """Получение информации о обученной модели"""
        if not self.training_successful:
            return {
                'status': 'Модель не обучена успешно',
                'best_model': 'Неизвестно',
                'forecast_length': self.forecast_length,
                'model_complexity': self.model_complexity
            }
        
        info = {
            'status': 'Обучена успешно',
            'best_model': self.best_model_name,
            'forecast_length': self.forecast_length,
            'frequency': self.frequency,
            'model_complexity': self.model_complexity
        }
        
        try:
            if hasattr(self.model, 'validation_results') and len(self.model.validation_results) > 0:
                best_score = self.model.validation_results.iloc[0]['Score']
                info['best_score'] = f"{best_score:.2f}"
                info['models_tested'] = len(self.model.validation_results)
        except:
            pass
            
        return info

def create_forecast(data, value_column, forecast_months, model_complexity='medium', frequency='ME'):
    """
    Универсальная функция для создания прогноза
    """
    model = UniversalForecastModel(
        forecast_length=forecast_months,
        frequency=frequency,
        model_complexity=model_complexity
    )
    
    success = model.train(data, value_column)
    
    if success:
        forecast = model.predict()
        return forecast, model, True
    else:
        # Все равно пытаемся создать простой прогноз
        forecast = model._simple_trend_forecast()
        return forecast, model, forecast is not None

# Специализированные функции для удобства
def create_apartment_forecast(data, forecast_months, model_complexity='medium'):
    """Создание прогноза для цен на квартиры"""
    return create_forecast(data, 'price', forecast_months, model_complexity, 'ME')

def create_salary_forecast(data, forecast_months, model_complexity='medium'):
    """Создание прогноза для зарплат"""
    return create_forecast(data, 'salary', forecast_months, model_complexity, 'ME')