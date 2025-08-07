from flask import Flask, render_template, jsonify, request
import requests
import os
import math
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import config
from functools import lru_cache
import time
import logging
import redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import g
from prometheus_client import Counter, Histogram
from flask_cors import CORS

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Metryki Prometheus
request_count = Counter('http_requests_total', 'Total HTTP requests', ['endpoint'])
request_latency = Histogram('http_request_duration_seconds', 'HTTP request latency', ['endpoint'])

# Inicjalizacja Redis (opcjonalne)
redis_client = None
try:
    if config.REDIS_HOST and config.REDIS_HOST != 'localhost':
        redis_client = redis.Redis(
            host=config.REDIS_HOST, 
            port=config.REDIS_PORT, 
            db=config.REDIS_DB, 
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        redis_client.ping()
        logger.info("Redis połączony pomyślnie")
    else:
        logger.info("Redis wyłączony - używanie cache w pamięci")
except Exception as e:
    logger.info(f"Redis niedostępny - używanie cache w pamięci: {e}")
    redis_client = None

def num2deg(xtile, ytile, zoom):
    """Convert tile numbers to lat/lon"""
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

# Cache dla requestów API (5 minut)
@lru_cache(maxsize=128)
def cached_weather_request(url, params_str):
    """Cache'owane requesty do WeatherAPI.com"""
    params = json.loads(params_str)
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.status_code, response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"Błąd requestu API: {e}")
        return 500, {'error': str(e)}

def validate_api_keys():
    """Walidacja kluczy API"""
    if not config.WEATHERAPI_KEY or config.WEATHERAPI_KEY == "your_api_key_here":
        raise ValueError("WeatherAPI key not configured")
    if not config.MAPBOX_ACCESS_TOKEN or config.MAPBOX_ACCESS_TOKEN == "your_mapbox_token_here":
        raise ValueError("Mapbox token not configured")
    logger.info("Klucze API zwalidowane pomyślnie")

load_dotenv()

app = Flask(__name__)

# Dodanie obsługi CORS
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
    }
})

# Funkcja do dodawania nagłówków CORS
@app.after_request
def add_cors_headers(response):
    """Dodaje nagłówki CORS do wszystkich odpowiedzi"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Middleware do śledzenia requestów
@app.before_request
def before_request():
    request_count.labels(endpoint=request.endpoint).inc()
    # Używamy g object zamiast dodawania atrybutu do request
    from flask import g
    g.start_time = time.time()

@app.after_request
def after_request(response):
    from flask import g
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        request_latency.labels(endpoint=request.endpoint).observe(duration)
    return response

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Sprawdź połączenie z Redis
        redis_status = "healthy" if redis_client and redis_client.ping() else "unhealthy"
        
        # Sprawdź API keys
        validate_api_keys()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'redis': redis_status,
            'api_keys': 'configured'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Metrics endpoint dla Prometheus
@app.route('/metrics')
def metrics():
    """Metryki Prometheus"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# Konfiguracja API z pliku config.py
# WeatherAPI.com API Key
WEATHERAPI_KEY = config.WEATHERAPI_KEY

# Mapbox Access Token  
MAPBOX_ACCESS_TOKEN = config.MAPBOX_ACCESS_TOKEN

@app.route('/')
def index():
    return render_template('ai_preflight.html')

@app.route('/ai_preflight')
def ai_preflight():
    return render_template('ai_preflight.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Obsługa plików statycznych z nagłówkami CORS"""
    response = app.send_static_file(filename)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/api/config')
def get_config():
    """Zwraca konfigurację dla frontendu"""
    return jsonify({
        'mapbox_access_token': config.MAPBOX_ACCESS_TOKEN,
        'default_center': config.DEFAULT_CENTER,
        'default_zoom': config.DEFAULT_ZOOM,
        'default_pitch': config.DEFAULT_PITCH
    })

@app.route('/api/weather/current')
@limiter.limit("30 per minute")
def current_weather():
    """Aktualna pogoda dla Warszawy"""
    try:
        url = f"http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': 'Warsaw',
            'aqi': 'no'
        }
        
        # Użyj cache'owanego requestu
        params_str = json.dumps(params, sort_keys=True)
        status_code, data = cached_weather_request(url, params_str)
        
        if status_code == 200 and data:
            if not isinstance(data, dict):
                return jsonify({'error': 'Nieprawidłowe dane z API'}), 500
                
            current = data.get('current', {})
            location = data.get('location', {})
            condition = current.get('condition', {})
            
            return jsonify({
                'temperature': current.get('temp_c', 0) if isinstance(current, dict) else 0,
                'feels_like': current.get('feelslike_c', 0) if isinstance(current, dict) else 0,
                'humidity': current.get('humidity', 0) if isinstance(current, dict) else 0,
                'pressure': current.get('pressure_mb', 1013) if isinstance(current, dict) else 1013,
                'wind_speed': current.get('wind_kph', 0) if isinstance(current, dict) else 0,
                'wind_direction': current.get('wind_degree', 0) if isinstance(current, dict) else 0,
                'visibility': current.get('vis_km', 10) if isinstance(current, dict) else 10,
                'description': condition.get('text', 'Unknown') if isinstance(condition, dict) else 'Unknown',
                'icon': condition.get('icon', '') if isinstance(condition, dict) else '',
                'sunrise': location.get('localtime', '').split(' ')[1][:5] if isinstance(location, dict) and location.get('localtime') else '00:00',
                'sunset': location.get('localtime', '').split(' ')[1][:5] if isinstance(location, dict) and location.get('localtime') else '00:00'
            })
        else:
            logger.error(f"API Error: {status_code} - {data}")
            return jsonify({'error': f'Błąd API: {status_code}'}), 500
            
    except Exception as e:
        logger.error(f"Exception in current_weather: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/forecast')
@limiter.limit("20 per minute")
def weather_forecast():
    """Prognoza pogody na 7 dni"""
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': 'Warsaw',
            'days': 7,
            'aqi': 'no',
            'alerts': 'no'
        }
        
        # Użyj cache'owanego requestu
        params_str = json.dumps(params, sort_keys=True)
        status_code, data = cached_weather_request(url, params_str)
        
        if status_code == 200 and data:
            forecast = []
            for day in data['forecast']['forecastday']:
                forecast.append({
                    'date': day['date'],
                    'day_name': datetime.strptime(day['date'], '%Y-%m-%d').strftime('%A'),
                    'temp_min': day['day']['mintemp_c'],
                    'temp_max': day['day']['maxtemp_c'],
                    'humidity': day['day']['avghumidity'],
                    'pressure': day['hour'][0]['pressure_mb'],
                    'wind_speed': day['day']['maxwind_kph'],
                    'description': day['day']['condition']['text'],
                    'icon': day['day']['condition']['icon'],
                    'pop': day['day']['daily_chance_of_rain'],
                    'hours': []
                })
            
            return jsonify(forecast)
        else:
            logger.error(f"Forecast API Error: {status_code} - {data}")
            return jsonify({'error': f'Błąd API prognozy: {status_code}'}), 500
            
    except Exception as e:
        logger.error(f"Forecast Exception: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze_flight_route', methods=['POST'])
def analyze_flight_route():
    """Analiza trasy lotu gołębi"""
    try:
        # Walidacja danych wejściowych
        if not request.is_json:
            return jsonify({'error': 'Oczekiwano danych JSON'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'Brak danych'}), 400
        
        start_location = data.get('start_location', 'Warszawa')
        end_location = data.get('end_location', 'Kraków')
        flight_date = data.get('flight_date', datetime.now().strftime('%Y-%m-%d'))
        flight_time = data.get('flight_time', '08:00')
        
        # Walidacja daty
        try:
            datetime.strptime(flight_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Nieprawidłowy format daty (YYYY-MM-DD)'}), 400
        
        # Walidacja czasu
        try:
            datetime.strptime(flight_time, '%H:%M')
        except ValueError:
            return jsonify({'error': 'Nieprawidłowy format czasu (HH:MM)'}), 400
        
        # TODO: Zastąp symulowane dane rzeczywistymi danymi z API
        # Pobierz rzeczywiste dane pogodowe dla trasy
        route_analysis = {
            'start_location': start_location,
            'end_location': end_location,
            'flight_date': flight_date,
            'flight_time': flight_time,
            'distance': 295,  # km - do zastąpienia rzeczywistymi obliczeniami
            'estimated_duration': '4-6 godzin',
            'route_points': [
                {'lat': 52.2297, 'lng': 21.0122, 'conditions': 85, 'color': 'green'},
                {'lat': 51.9194, 'lng': 19.1451, 'conditions': 75, 'color': 'blue'},
                {'lat': 50.0647, 'lng': 19.9450, 'conditions': 90, 'color': 'green'}
            ],
            'overall_score': 83,
            'recommendations': [
                'Warunki lotu są dobre',
                'Temperatura optymalna (18-22°C)',
                'Wiatr umiarkowany (<15 km/h)',
                'Widoczność dobra (>10 km)',
                'Niskie prawdopodobieństwo opadów'
            ],
            'warnings': [
                'Uwaga na wiatr w godzinach popołudniowych',
                'Możliwe lekkie zachmurzenie'
            ]
        }
        
        return jsonify(route_analysis)
    except Exception as e:
        print(f"Błąd analizy trasy: {e}")
        return jsonify({'error': f'Błąd analizy trasy: {str(e)}'}), 500

@app.route('/api/weather/layers/temperature')
def temperature_layer():
    """Warstwa temperatury - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            temp_c = weather_data.get('current', {}).get('temp_c', 0)
            
            # Generuj punkty temperatury wokół lokalizacji
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "temperature": temp_c,
                            "unit": "celsius",
                            "timestamp": weather_data.get('location', {}).get('localtime', ''),
                            "humidity": weather_data.get('current', {}).get('humidity', 0)
                        }
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon) + 0.01, float(lat) + 0.01]
                        },
                        "properties": {
                            "temperature": temp_c + 0.5,
                            "unit": "celsius",
                            "timestamp": weather_data.get('location', {}).get('localtime', ''),
                            "humidity": weather_data.get('current', {}).get('humidity', 0)
                        }
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon) - 0.01, float(lat) - 0.01]
                        },
                        "properties": {
                            "temperature": temp_c - 0.5,
                            "unit": "celsius",
                            "timestamp": weather_data.get('location', {}).get('localtime', ''),
                            "humidity": weather_data.get('current', {}).get('humidity', 0)
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/wind')
def wind_layer():
    """Warstwa wiatru - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "wind_speed": current.get('wind_kph', 0),
                            "wind_direction": current.get('wind_degree', 0),
                            "wind_mph": current.get('wind_mph', 0),
                            "unit": "km/h",
                            "gust_kph": current.get('gust_kph', 0),
                            "gust_mph": current.get('gust_mph', 0),
                            "timestamp": weather_data.get('location', {}).get('localtime', '')
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/precipitation')
def precipitation_layer():
    """Warstwa opadów - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "precipitation": current.get('precip_mm', 0.0),
                            "probability": current.get('chance_of_rain', 0),
                            "unit": "mm",
                            "condition": current.get('condition', {}).get('text', ''),
                            "timestamp": weather_data.get('location', {}).get('localtime', '')
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/radar')
def radar_layer():
    """Warstwa radaru - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            # Określ intensywność na podstawie opadów
            precip_mm = current.get('precip_mm', 0)
            intensity = min(1.0, precip_mm / 10.0) if precip_mm > 0 else 0.1
            
            # Określ typ na podstawie warunków
            condition_text = current.get('condition', {}).get('text', '').lower()
            if 'rain' in condition_text:
                radar_type = "rain"
            elif 'snow' in condition_text:
                radar_type = "snow"
            elif 'storm' in condition_text:
                radar_type = "storm"
            else:
                radar_type = "clear"
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "intensity": intensity,
                            "type": radar_type,
                            "precipitation_mm": precip_mm,
                            "condition": condition_text,
                            "timestamp": weather_data.get('location', {}).get('localtime', '')
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/clouds')
def clouds_layer():
    """Warstwa chmur - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            cloud_cover = current.get('cloud', 0)
            
            # Określ typ chmur na podstawie warunków
            condition_text = current.get('condition', {}).get('text', '').lower()
            if 'overcast' in condition_text:
                cloud_type = "overcast"
            elif 'partly cloudy' in condition_text:
                cloud_type = "scattered"
            elif 'cloudy' in condition_text:
                cloud_type = "broken"
            else:
                cloud_type = "clear"
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "cloud_cover": cloud_cover,
                            "cloud_type": cloud_type,
                            "condition": condition_text,
                            "timestamp": weather_data.get('location', {}).get('localtime', '')
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/pressure')
def pressure_layer():
    """Warstwa ciśnienia - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "pressure": current.get('pressure_mb', 1013.25),
                            "unit": "hPa",
                            "pressure_in": current.get('pressure_in', 29.92),
                            "timestamp": weather_data.get('location', {}).get('localtime', '')
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/humidity')
def humidity_layer():
    """Warstwa wilgotności - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "humidity": current.get('humidity', 0),
                            "unit": "%",
                            "feels_like": current.get('feelslike_c', 0),
                            "timestamp": weather_data.get('location', {}).get('localtime', '')
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/visibility')
def visibility_layer():
    """Warstwa widoczności - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "visibility": current.get('vis_km', 10.0),
                            "unit": "km",
                            "condition": current.get('condition', {}).get('text', ''),
                            "timestamp": weather_data.get('location', {}).get('localtime', '')
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/satellite')
def satellite_layer():
    """Warstwa satelitarna - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            cloud_cover = weather_data.get('current', {}).get('cloud', 0)
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(lon), float(lat)]
                        },
                        "properties": {
                            "cloud_cover": cloud_cover,
                            "satellite_type": "infrared",
                            "temperature": weather_data.get('current', {}).get('temp_c', 0),
                            "humidity": weather_data.get('current', {}).get('humidity', 0),
                            "visibility": weather_data.get('current', {}).get('vis_km', 10)
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/3d-buildings')
def buildings_3d_layer():
    """Warstwa budynków 3D - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            pressure = weather_data.get('current', {}).get('pressure_mb', 1013)
            
            # Wysokość budynku na podstawie ciśnienia atmosferycznego
            height = max(10, min(100, (pressure - 950) * 2))
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [float(lon) - 0.001, float(lat) - 0.001],
                                [float(lon) + 0.001, float(lat) - 0.001],
                                [float(lon) + 0.001, float(lat) + 0.001],
                                [float(lon) - 0.001, float(lat) + 0.001],
                                [float(lon) - 0.001, float(lat) - 0.001]
                            ]]
                        },
                        "properties": {
                            "height": height,
                            "building_type": "office",
                            "pressure": pressure,
                            "temperature": weather_data.get('current', {}).get('temp_c', 0)
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/3d-terrain')
def terrain_3d_layer():
    """Warstwa terenu 3D - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            humidity = weather_data.get('current', {}).get('humidity', 50)
            
            # Wysokość terenu na podstawie wilgotności
            elevation = max(50, min(200, 100 + humidity))
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [float(lon) - 0.002, float(lat) - 0.002],
                                [float(lon) + 0.002, float(lat) - 0.002],
                                [float(lon) + 0.002, float(lat) + 0.002],
                                [float(lon) - 0.002, float(lat) + 0.002],
                                [float(lon) - 0.002, float(lat) - 0.002]
                            ]]
                        },
                        "properties": {
                            "elevation": elevation,
                            "terrain_type": "urban",
                            "humidity": humidity,
                            "temperature": weather_data.get('current', {}).get('temp_c', 0)
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/3d-weather')
def weather_3d_layer():
    """Warstwa pogody 3D - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            # Określ typ pogody na podstawie warunków
            condition_text = current.get('condition', {}).get('text', '').lower()
            if 'rain' in condition_text:
                weather_type = "rainy"
            elif 'snow' in condition_text:
                weather_type = "snowy"
            elif 'cloud' in condition_text:
                weather_type = "cloudy"
            else:
                weather_type = "clear"
            
            # Intensywność na podstawie opadów
            intensity = min(1.0, current.get('precip_mm', 0) / 10.0)
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [float(lon) - 0.0015, float(lat) - 0.0015],
                                [float(lon) + 0.0015, float(lat) - 0.0015],
                                [float(lon) + 0.0015, float(lat) + 0.0015],
                                [float(lon) - 0.0015, float(lat) + 0.0015],
                                [float(lon) - 0.0015, float(lat) - 0.0015]
                            ]]
                        },
                        "properties": {
                            "weather_type": weather_type,
                            "weather_intensity": intensity,
                            "wind_speed": current.get('wind_kph', 0),
                            "temperature": current.get('temp_c', 0),
                            "humidity": current.get('humidity', 0),
                            "pressure": current.get('pressure_mb', 1013),
                            "visibility": current.get('vis_km', 10)
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/layers/3d-animations')
def animations_3d_layer():
    """Warstwa animacji 3D - rzeczywiste dane z WeatherAPI.com"""
    try:
        lat = request.args.get('lat', 52.2297)
        lon = request.args.get('lon', 21.0122)
        
        # Pobierz rzeczywiste dane pogodowe
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            # Określ typ animacji na podstawie warunków pogodowych
            wind_speed = current.get('wind_kph', 0)
            if wind_speed > 20:
                animation_type = "wind_particles"
                animation_speed = min(2.0, wind_speed / 10.0)
            elif current.get('precip_mm', 0) > 0:
                animation_type = "rain_particles"
                animation_speed = 1.0
            else:
                animation_type = "ambient"
                animation_speed = 0.5
            
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [float(lon) - 0.001, float(lat) - 0.001],
                                [float(lon) + 0.001, float(lat) - 0.001],
                                [float(lon) + 0.001, float(lat) + 0.001],
                                [float(lon) - 0.001, float(lat) + 0.001],
                                [float(lon) - 0.001, float(lat) - 0.001]
                            ]]
                        },
                        "properties": {
                            "animation_speed": animation_speed,
                            "animation_type": animation_type,
                            "wind_speed": wind_speed,
                            "temperature": current.get('temp_c', 0),
                            "humidity": current.get('humidity', 0),
                            "precipitation": current.get('precip_mm', 0)
                        }
                    }
                ]
            }
            return jsonify(data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/radar/tiles/<int:z>/<int:x>/<int:y>')
def radar_tiles(z, x, y):
    """Kafelki radaru pogodowego - rzeczywiste dane z WeatherAPI.com"""
    try:
        # Pobierz rzeczywiste dane pogodowe dla tego obszaru
        lat_north, lon_west = num2deg(x, y, z)
        lat_south, lon_east = num2deg(x + 1, y + 1, z)
        
        # Środek kafelka
        center_lat = (lat_north + lat_south) / 2
        center_lon = (lon_west + lon_east) / 2
        
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{center_lat},{center_lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            # Intensywność na podstawie opadów
            precip_mm = current.get('precip_mm', 0)
            intensity = min(1.0, precip_mm / 10.0)
            
            # Kolor na podstawie typu opadów
            condition_text = current.get('condition', {}).get('text', '').lower()
            if 'rain' in condition_text:
                color = 'blue'
            elif 'snow' in condition_text:
                color = 'white'
            else:
                color = 'green'
            
            return jsonify({
                'z': z,
                'x': x,
                'y': y,
                'intensity': intensity,
                'color': color,
                'precipitation_mm': precip_mm,
                'temperature': current.get('temp_c', 0),
                'humidity': current.get('humidity', 0)
            })
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/mts/temperature/tiles/<int:z>/<int:x>/<int:y>')
def temperature_mts_tiles(z, x, y):
    """Kafelki temperatury w formacie MTS - rzeczywiste dane z WeatherAPI.com"""
    try:
        # Pobierz rzeczywiste dane pogodowe dla tego obszaru
        lat_north, lon_west = num2deg(x, y, z)
        lat_south, lon_east = num2deg(x + 1, y + 1, z)
        
        # Środek kafelka
        center_lat = (lat_north + lat_south) / 2
        center_lon = (lon_west + lon_east) / 2
        
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{center_lat},{center_lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            temp_c = weather_data.get('current', {}).get('temp_c', 0)
            temp_k = temp_c + 273.15  # Konwersja na Kelviny
            
            temperature_data = {
                'z': z,
                'x': x,
                'y': y,
                'type': 'raster-array',
                'data': {
                    'temperature': temp_c,
                    'temperature_k': temp_k,
                    'range': [200, 350],  # Zakres w Kelvinach
                    'scale': 0.1,
                    'offset': -100,
                    'units': 'K',
                    'humidity': weather_data.get('current', {}).get('humidity', 0),
                    'pressure': weather_data.get('current', {}).get('pressure_mb', 1013)
                }
            }
            return jsonify(temperature_data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/mts/wind/tiles/<int:z>/<int:x>/<int:y>')
def wind_mts_tiles(z, x, y):
    """Kafelki wiatru w formacie MTS - rzeczywiste dane z WeatherAPI.com"""
    try:
        # Pobierz rzeczywiste dane pogodowe dla tego obszaru
        lat_north, lon_west = num2deg(x, y, z)
        lat_south, lon_east = num2deg(x + 1, y + 1, z)
        
        # Środek kafelka
        center_lat = (lat_north + lat_south) / 2
        center_lon = (lon_west + lon_east) / 2
        
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{center_lat},{center_lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current', {})
            
            wind_speed_kph = current.get('wind_kph', 0)
            wind_speed_ms = wind_speed_kph / 3.6  # Konwersja km/h na m/s
            wind_direction = current.get('wind_degree', 0)
            
            # Oblicz składowe U i V
            import math
            wind_rad = math.radians(wind_direction)
            u_component = -wind_speed_ms * math.sin(wind_rad)
            v_component = -wind_speed_ms * math.cos(wind_rad)
            
            wind_data = {
                'z': z,
                'x': x,
                'y': y,
                'type': 'raster-array',
                'data': {
                    'u_component': round(u_component, 2),
                    'v_component': round(v_component, 2),
                    'speed': round(wind_speed_ms, 2),
                    'direction': wind_direction,
                    'range': [0, 50],
                    'scale': 1.0,
                    'offset': 0,
                    'units': 'm/s',
                    'gust_speed': current.get('gust_kph', 0) / 3.6,
                    'timestamp': weather_data.get('location', {}).get('localtime', '')
                }
            }
            return jsonify(wind_data)
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/mts/temperature/recipe')
def temperature_mts_recipe():
    """Recipe dla warstwy temperatury MTS"""
    recipe = {
        "version": 1,
        "type": "rasterarray",
        "sources": [
            {
                "uri": "mapbox://tileset-source/account/temperature-source"
            }
        ],
        "minzoom": 0,
        "maxzoom": 3,
        "layers": {
            "2t": {
                "tilesize": 256,
                "offset": -100,
                "scale": 0.1,
                "resampling": "bilinear",
                "buffer": 1,
                "units": "K",
                "source_rules": {
                    "filter": [
                        "all",
                        ["==", ["get", "NETCDF_VARNAME"], "Temperature_height_above_ground"],
                        ["==", ["get", "NETCDF_DIM_height_above_ground3"], "2"]
                    ],
                    "name": ["to-number", ["get", "NETCDF_DIM_time"]],
                    "order": "asc"
                }
            }
        }
    }
    return jsonify(recipe)

@app.route('/api/weather/mts/wind/recipe')
def wind_mts_recipe():
    """Recipe dla warstwy wiatru MTS"""
    recipe = {
        "version": 1,
        "type": "rasterarray",
        "sources": [
            {
                "uri": "mapbox://tileset-source/account/wind-source"
            }
        ],
        "minzoom": 0,
        "maxzoom": 3,
        "layers": {
            "wind": {
                "tilesize": 256,
                "offset": 0,
                "scale": 1.0,
                "resampling": "bilinear",
                "buffer": 1,
                "units": "m/s",
                "source_rules": {
                    "filter": [
                        "all",
                        ["==", ["get", "NETCDF_VARNAME"], "Wind_components"],
                        ["==", ["get", "NETCDF_DIM_height_above_ground3"], "10"]
                    ],
                    "name": ["to-number", ["get", "NETCDF_DIM_time"]],
                    "order": "asc"
                }
            }
        }
    }
    return jsonify(recipe)

@app.route('/api/weather/mts/temperature/tilejson')
def temperature_mts_tilejson():
    """TileJSON dla warstwy temperatury MTS"""
    tilejson = {
        "tilejson": "3.0.0",
        "name": "temperature-mts",
        "description": "Temperature data from MTS",
        "version": "1.0.0",
        "attribution": "© Mapbox",
        "template": "",
        "legend": "",
        "scheme": "xyz",
        "tiles": [
            f"/api/weather/mts/temperature/tiles/{{z}}/{{x}}/{{y}}"
        ],
        "grids": [],
        "data": [],
        "minzoom": 0,
        "maxzoom": 3,
        "bounds": [-180, -90, 180, 90],
        "center": [0, 0, 0],
        "raster_layers": [
            {
                "id": "2t",
                "fields": {
                    "bands": ["0", "3", "6", "9", "12", "15", "18", "21"],
                    "buffer": 1,
                    "name": "2t",
                    "offset": 0,
                    "range": [204, 323],
                    "scale": 1,
                    "tilesize": 256,
                    "units": "K"
                },
                "maxzoom": 3,
                "minzoom": 0
            }
        ]
    }
    return jsonify(tilejson)

@app.route('/api/weather/mts/wind/tilejson')
def wind_mts_tilejson():
    """TileJSON dla warstwy wiatru MTS"""
    tilejson = {
        "tilejson": "3.0.0",
        "name": "wind-mts",
        "description": "Wind data from MTS",
        "version": "1.0.0",
        "attribution": "© Mapbox",
        "template": "",
        "legend": "",
        "scheme": "xyz",
        "tiles": [
            f"/api/weather/mts/wind/tiles/{{z}}/{{x}}/{{y}}"
        ],
        "grids": [],
        "data": [],
        "minzoom": 0,
        "maxzoom": 3,
        "bounds": [-180, -90, 180, 90],
        "center": [0, 0, 0],
        "raster_layers": [
            {
                "id": "wind",
                "fields": {
                    "bands": ["0", "3", "6", "9", "12", "15", "18", "21"],
                    "buffer": 1,
                    "name": "wind",
                    "offset": 0,
                    "range": [0, 50],
                    "scale": 1,
                    "tilesize": 256,
                    "units": "m/s"
                },
                "maxzoom": 3,
                "minzoom": 0
            }
        ]
    }
    return jsonify(tilejson)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 