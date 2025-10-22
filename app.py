import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Импорт наших модулей
from auth import render_auth_sidebar
from api_clients import AvitoAPIClient, HHAPIClient, get_available_regions, get_available_languages
from models import create_apartment_forecast, create_salary_forecast

# Настройки страницы
st.set_page_config(
    page_title="📊 Прогнозная аналитика",
    layout="wide",
    initial_sidebar_state="expanded"
)

def render_apartment_forecast():
    """Интерфейс для прогноза цен на квартиры"""
    st.header("🏠 Прогноз цен на квартиры")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        region = st.selectbox("Выберите регион", get_available_regions(), key="apartment_region")
        rooms = st.selectbox("Количество комнат", ["1", "2", "3", "4+"], key="apartment_rooms")
    
    with col2:
        period = st.slider("Период данных (месяцы)", 6, 60, 24, key="apartment_period")
        forecast_months = st.slider("Период прогноза (месяцы)", 3, 24, 12, key="apartment_forecast")
    
    # Выбор сложности модели
    model_complexity = st.selectbox(
        "Сложность моделей",
        ["simple", "medium", "complex", "all"],
        index=1,
        format_func=lambda x: {
            "simple": "🟢 Простые (быстро)",
            "medium": "🟡 Средние (рекомендуется)", 
            "complex": "🟠 Сложные (медленнее)",
            "all": "🔴 Все модели (очень медленно)"
        }[x],
        key="apartment_model_complexity"
    )
    
    if st.button("📈 Получить прогноз", key="apartment_btn"):
        if 'avito' not in st.session_state.tokens:
            st.warning("⚠️ Для работы с Avito API требуется токен. Введите его в настройках слева.")
            return
        
        with st.spinner("Получение данных из API..."):
            client = AvitoAPIClient(st.session_state.tokens['avito'])
            data = client.get_apartment_prices(region, rooms, period)
            
            if data is not None:
                st.success(f"✅ Получено {len(data)} записей")
                
                # Отображение исходных данных
                st.subheader("Исторические данные")
                st.dataframe(data.tail(10), width='stretch')
                
                # Статистика данных
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("Средняя цена", f"{data['price'].mean():,.0f} ₽")
                with col_stat2:
                    st.metric("Минимальная цена", f"{data['price'].min():,.0f} ₽")
                with col_stat3:
                    st.metric("Максимальная цена", f"{data['price'].max():,.0f} ₽")
                
                # Создание прогноза
                with st.spinner("Обучение модели и создание прогноза..."):
                    forecast, model, success = create_apartment_forecast(data, forecast_months, model_complexity)
                    
                    if success and forecast is not None:
                        # Визуализация
                        fig = make_subplots(
                            rows=1, cols=1,
                            subplot_titles=[f"Прогноз цен на квартиры ({region}, {rooms} ком.)"]
                        )
                        
                        # Исторические данные
                        fig.add_trace(
                            go.Scatter(
                                x=data['date'], 
                                y=data['price'], 
                                name='Исторические данные', 
                                line=dict(color='blue', width=2),
                                mode='lines+markers'
                            )
                        )
                        
                        # Прогноз
                        forecast_dates = forecast.index
                        forecast_values = forecast.iloc[:, 0]
                        
                        fig.add_trace(
                            go.Scatter(
                                x=forecast_dates, 
                                y=forecast_values, 
                                name='Прогноз', 
                                line=dict(color='red', width=2, dash='dash'),
                                mode='lines+markers'
                            )
                        )
                        
                        # Область уверенности (если доступна)
                        try:
                            if hasattr(model.model, 'prediction_intervals'):
                                upper_bound = forecast_values * 1.1  # Пример: +10%
                                lower_bound = forecast_values * 0.9  # Пример: -10%
                                
                                fig.add_trace(
                                    go.Scatter(
                                        x=forecast_dates.tolist() + forecast_dates.tolist()[::-1],
                                        y=upper_bound.tolist() + lower_bound.tolist()[::-1],
                                        fill='toself',
                                        fillcolor='rgba(255,0,0,0.2)',
                                        line=dict(color='rgba(255,255,255,0)'),
                                        name='Диапазон прогноза'
                                    )
                                )
                        except:
                            pass
                        
                        fig.update_layout(
                            xaxis_title="Дата",
                            yaxis_title="Цена (руб)",
                            height=500,
                            showlegend=True
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Информация о модели
                        if hasattr(model, 'get_model_info'):
                            model_info = model.get_model_info()
                            st.subheader("Информация о модели")
                            col_info1, col_info2 = st.columns(2)
                            with col_info1:
                                st.write(f"**Лучшая модель:** {model_info.get('best_model', 'Неизвестно')}")
                                st.write(f"**Сложность:** {model_info.get('model_complexity', 'Неизвестно')}")
                            with col_info2:
                                st.write(f"**Период прогноза:** {model_info.get('forecast_length', 'Неизвестно')} месяцев")
                                if 'best_score' in model_info:
                                    st.write(f"**Точность (RMSE):** {model_info['best_score']:.2f}")
                        
                        # Показать прогноз в таблице
                        st.subheader("Данные прогноза")
                        forecast_df = forecast.reset_index()
                        forecast_df.columns = ['Дата', 'Прогнозируемая цена']
                        forecast_df['Прогнозируемая цена'] = forecast_df['Прогнозируемая цена'].round(2)
                        st.dataframe(forecast_df, width='stretch')
                        
                        # Скачивание прогноза
                        csv = forecast_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Скачать прогноз как CSV",
                            data=csv,
                            file_name=f"прогноз_квартиры_{region}_{rooms}к_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                            mime='text/csv',
                        )
                    else:
                        st.error("❌ Не удалось создать прогноз. Попробуйте изменить параметры или увеличить период данных.")

def render_salary_forecast():
    """Интерфейс для прогноза зарплат"""
    st.header("💼 Прогноз зарплатных ожиданий")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        language = st.selectbox("Язык программирования", get_available_languages(), key="salary_language")
    
    with col2:
        period = st.slider("Период данных (месяцы)", 6, 60, 24, key="salary_period")
        forecast_months = st.slider("Период прогноза (месяцы)", 3, 24, 12, key="salary_forecast")
    
    # Выбор сложности модели
    model_complexity = st.selectbox(
        "Сложность моделей",
        ["simple", "medium", "complex", "all"],
        index=1,
        format_func=lambda x: {
            "simple": "🟢 Простые (быстро)",
            "medium": "🟡 Средние (рекомендуется)", 
            "complex": "🟠 Сложные (медленнее)",
            "all": "🔴 Все модели (очень медленно)"
        }[x],
        key="salary_model_complexity"
    )
    
    if st.button("📊 Получить прогноз", key="salary_btn"):
        if 'hh' not in st.session_state.tokens:
            st.warning("⚠️ Для работы с HH API требуется токен. Введите его в настройках слева.")
            return
        
        with st.spinner("Получение данных из API..."):
            client = HHAPIClient(st.session_state.tokens['hh'])
            data = client.get_salary_data(language, period)
            
            if data is not None:
                st.success(f"✅ Получено {len(data)} записей")
                
                # Отображение исходных данных
                st.subheader("Исторические данные")
                st.dataframe(data.tail(10), width='stretch')
                
                # Статистика данных
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("Средняя зарплата", f"{data['salary'].mean():,.0f} ₽")
                with col_stat2:
                    st.metric("Минимальная зарплата", f"{data['salary'].min():,.0f} ₽")
                with col_stat3:
                    st.metric("Максимальная зарплата", f"{data['salary'].max():,.0f} ₽")
                
                # Создание прогноза
                with st.spinner("Обучение модели и создание прогноза..."):
                    forecast, model, success = create_salary_forecast(data, forecast_months, model_complexity)
                    
                    if success and forecast is not None:
                        # Визуализация
                        fig = make_subplots(
                            rows=1, cols=1,
                            subplot_titles=[f"Прогноз зарплат для {language} разработчиков"]
                        )
                        
                        # Исторические данные
                        fig.add_trace(
                            go.Scatter(
                                x=data['date'], 
                                y=data['salary'], 
                                name='Исторические данные', 
                                line=dict(color='green', width=2),
                                mode='lines+markers'
                            )
                        )
                        
                        # Прогноз
                        forecast_dates = forecast.index
                        forecast_values = forecast.iloc[:, 0]
                        
                        fig.add_trace(
                            go.Scatter(
                                x=forecast_dates, 
                                y=forecast_values, 
                                name='Прогноз', 
                                line=dict(color='orange', width=2, dash='dash'),
                                mode='lines+markers'
                            )
                        )
                        
                        # Область уверенности
                        try:
                            upper_bound = forecast_values * 1.1
                            lower_bound = forecast_values * 0.9
                            
                            fig.add_trace(
                                go.Scatter(
                                    x=forecast_dates.tolist() + forecast_dates.tolist()[::-1],
                                    y=upper_bound.tolist() + lower_bound.tolist()[::-1],
                                    fill='toself',
                                    fillcolor='rgba(255,165,0,0.2)',
                                    line=dict(color='rgba(255,255,255,0)'),
                                    name='Диапазон прогноза'
                                )
                            )
                        except:
                            pass
                        
                        fig.update_layout(
                            xaxis_title="Дата",
                            yaxis_title="Зарплата (руб)",
                            height=500,
                            showlegend=True
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Информация о модели
                        if hasattr(model, 'get_model_info'):
                            model_info = model.get_model_info()
                            st.subheader("Информация о модели")
                            col_info1, col_info2 = st.columns(2)
                            with col_info1:
                                st.write(f"**Лучшая модель:** {model_info.get('best_model', 'Неизвестно')}")
                                st.write(f"**Сложность:** {model_info.get('model_complexity', 'Неизвестно')}")
                            with col_info2:
                                st.write(f"**Период прогноза:** {model_info.get('forecast_length', 'Неизвестно')} месяцев")
                                if 'best_score' in model_info:
                                    st.write(f"**Точность (RMSE):** {model_info['best_score']:.2f}")
                        
                        # Показать прогноз в таблице
                        st.subheader("Данные прогноза")
                        forecast_df = forecast.reset_index()
                        forecast_df.columns = ['Дата', 'Прогнозируемая зарплата']
                        forecast_df['Прогнозируемая зарплата'] = forecast_df['Прогнозируемая зарплата'].round(2)
                        st.dataframe(forecast_df, width='stretch')
                        
                        # Скачивание прогноза
                        csv = forecast_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Скачать прогноз как CSV",
                            data=csv,
                            file_name=f"прогноз_зарплат_{language}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                            mime='text/csv',
                        )
                    else:
                        st.error("❌ Не удалось создать прогноз. Попробуйте изменить параметры или увеличить период данных.")

def render_demo_mode():
    """Режим демонстрации без API токенов"""
    st.info("🔸 **Демонстрационный режим** - используются сгенерированные данные")
    
    tab1, tab2 = st.tabs(["🏠 Цены на квартиры", "💼 Зарплаты разработчиков"])
    
    with tab1:
        st.subheader("Демо: Прогноз цен на квартиры")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            region = st.selectbox("Выберите регион", get_available_regions(), key="demo_apartment_region")
            rooms = st.selectbox("Количество комнат", ["1", "2", "3", "4+"], key="demo_apartment_rooms")
        
        with col2:
            period = st.slider("Период данных (месяцы)", 6, 60, 24, key="demo_apartment_period")
            forecast_months = st.slider("Период прогноза (месяцы)", 3, 24, 12, key="demo_apartment_forecast")
        
        model_complexity = st.selectbox(
            "Сложность моделей",
            ["simple", "medium"],
            index=1,
            key="demo_apartment_model_complexity"
        )
        
        if st.button("🎯 Запустить демо-прогноз", key="demo_apartment_btn"):
            with st.spinner("Генерация демо-данных..."):
                # Используем демо-клиент без токена
                client = AvitoAPIClient("demo-token")
                data = client.get_apartment_prices(region, rooms, period)
                
                if data is not None:
                    st.success(f"✅ Сгенерировано {len(data)} демо-записей")
                    
                    # Создание прогноза
                    with st.spinner("Обучение модели на демо-данных..."):
                        forecast, model, success = create_apartment_forecast(data, forecast_months, model_complexity)
                        
                        if success and forecast is not None:
                            # Упрощенная визуализация для демо
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=data['date'], y=data['price'], name='Исторические данные'))
                            fig.add_trace(go.Scatter(x=forecast.index, y=forecast.iloc[:, 0], name='Прогноз'))
                            fig.update_layout(title=f"Демо-прогноз: {region}, {rooms} ком.")
                            st.plotly_chart(fig, use_container_width=True)
                            
                            st.info("💡 Это демонстрационный прогноз на сгенерированных данных. Для реальных данных введите API токены.")
                        else:
                            st.error("Демо-прогноз не удался. Попробуйте другие параметры.")
    
    with tab2:
        st.subheader("Демо: Прогноз зарплат")
        
        language = st.selectbox("Язык программирования", get_available_languages(), key="demo_salary_language")
        forecast_months = st.slider("Период прогноза (месяцы)", 3, 12, 6, key="demo_salary_forecast")
        
        if st.button("🎯 Запустить демо-прогноз зарплат", key="demo_salary_btn"):
            with st.spinner("Генерация демо-данных..."):
                client = HHAPIClient("demo-token")
                data = client.get_salary_data(language, 24)  # Фиксированный период для демо
                
                if data is not None:
                    st.success(f"✅ Сгенерировано {len(data)} демо-записей")
                    
                    with st.spinner("Обучение модели на демо-данных..."):
                        forecast, model, success = create_salary_forecast(data, forecast_months, "simple")
                        
                        if success and forecast is not None:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=data['date'], y=data['salary'], name='Исторические данные'))
                            fig.add_trace(go.Scatter(x=forecast.index, y=forecast.iloc[:, 0], name='Прогноз'))
                            fig.update_layout(title=f"Демо-прогноз зарплат: {language}")
                            st.plotly_chart(fig, use_container_width=True)
                            
                            st.info("💡 Это демонстрационный прогноз на сгенерированных данных. Для реальных данных введите API токены.")

def main():
    """Основная функция приложения"""
    st.title("📊 Система прогнозной аналитики")
    
    # Аутентификация
    is_authenticated = render_auth_sidebar()
    
    if not is_authenticated:
        st.info("👈 Пожалуйста, войдите в систему или зарегистрируйтесь")
        return
    
    # Основной интерфейс
    st.sidebar.title("🎯 Выбор раздела")
    
    app_mode = st.sidebar.radio(
        "Режим работы:",
        ["🏠 Предсказание цен на квартиры", "💼 Предсказание зарплатных ожиданий", "🔸 Демонстрационный режим"]
    )
    
    # Проверка наличия токенов
    has_avito_token = 'avito' in st.session_state.tokens and st.session_state.tokens['avito']
    has_hh_token = 'hh' in st.session_state.tokens and st.session_state.tokens['hh']
    
    if app_mode == "🏠 Предсказание цен на квартиры":
        if not has_avito_token:
            st.warning("""
            ⚠️ **Требуется токен Avito API**
            
            Для работы с реальными данными необходимо:
            1. Получить токен на [Avito для разработчиков](https://developers.avito.ru/)
            2. Ввести токен в настройках слева
            
            Или используйте **Демонстрационный режим** для тестирования.
            """)
            if st.button("Перейти в демонстрационный режим"):
                st.session_state.demo_redirect = True
                st.rerun()
        else:
            render_apartment_forecast()
    
    elif app_mode == "💼 Предсказание зарплатных ожиданий":
        if not has_hh_token:
            st.warning("""
            ⚠️ **Требуется токен HH API**
            
            Для работы с реальными данными необходимо:
            1. Получить токен на [HH.ru для разработчиков](https://dev.hh.ru/)
            2. Ввести токен в настройках слева
            
            Или используйте **Демонстрационный режим** для тестирования.
            """)
            if st.button("Перейти в демонстрационный режим"):
                st.session_state.demo_redirect = True
                st.rerun()
        else:
            render_salary_forecast()
    
    else:  # Демонстрационный режим
        render_demo_mode()
    
    # Информация в подвале
    st.sidebar.markdown("---")
    st.sidebar.info("""
    **О приложении:**
    - Прогнозирование на основе AutoTS
    - Поддержка множества моделей
    - Визуализация с Plotly
    """)

if __name__ == "__main__":
    main()