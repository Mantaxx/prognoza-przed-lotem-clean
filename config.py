# Konfiguracja API dla aplikacji Prognoza Przed Lotem
# Zastąp poniższe wartości swoimi prawdziwymi kluczami API

import os
from dotenv import load_dotenv

load_dotenv()

# WeatherAPI.com API Key - pobierz z https://www.weatherapi.com/
# Darmowy plan: 1,000,000 zapytań/miesiąc
WEATHERAPI_KEY = os.getenv('WEATHERAPI_KEY', "your_weatherapi_key_here")

# Mapbox Access Token - pobierz z https://account.mapbox.com/access-tokens/
MAPBOX_ACCESS_TOKEN = os.getenv('MAPBOX_ACCESS_TOKEN', "your_mapbox_token_here")

# Inne ustawienia
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

# Ustawienia mapy
DEFAULT_CENTER = [float(x) for x in os.getenv('DEFAULT_CENTER', '21.0122,52.2297').split(',')]  # Warszawa
DEFAULT_ZOOM = int(os.getenv('DEFAULT_ZOOM', 8))
DEFAULT_PITCH = int(os.getenv('DEFAULT_PITCH', 45))

# Ustawienia pogodowe
DEFAULT_CITY = os.getenv('DEFAULT_CITY', "Warsaw")
WEATHER_UNITS = os.getenv('WEATHER_UNITS', "metric")
WEATHER_LANGUAGE = os.getenv('WEATHER_LANGUAGE', "pl")

# Ustawienia animacji
DEFAULT_ANIMATION_SPEED = float(os.getenv('DEFAULT_ANIMATION_SPEED', 1.0))
TIMELINE_STEPS = int(os.getenv('TIMELINE_STEPS', 48))  # 30-minutowe interwały przez 24h

# Ustawienia analizy tras
ROUTE_ANALYSIS_POINTS = int(os.getenv('ROUTE_ANALYSIS_POINTS', 5))  # Liczba punktów analizy na trasie
MIN_FLIGHT_DISTANCE = int(os.getenv('MIN_FLIGHT_DISTANCE', 10))   # Minimalny dystans lotu w km
MAX_FLIGHT_DISTANCE = int(os.getenv('MAX_FLIGHT_DISTANCE', 1000)) # Maksymalny dystans lotu w km

# Ustawienia Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Ustawienia rate limiting
RATE_LIMIT_DAILY = os.getenv('RATE_LIMIT_DAILY', '200 per day')
RATE_LIMIT_HOURLY = os.getenv('RATE_LIMIT_HOURLY', '50 per hour') 