# Конфигурационные параметры
AVITO_API_CONFIG = {
    'base_url': 'https://api.avito.ru',
    'token': None  # Будет устанавливаться пользователем
}

HH_API_CONFIG = {
    'base_url': 'https://api.hh.ru',
    'token': None  # Будет устанавливаться пользователем
}

# Настройки моделей
MODEL_CONFIG = {
    'forecast_length': 12,
    'frequency': 'M',
    'models': 'MLP'
}