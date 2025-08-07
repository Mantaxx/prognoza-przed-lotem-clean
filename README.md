# 🌤️ Prognoza Przed Lotem - AI Weather Application

Zaawansowana aplikacja do analizy pogody i tras lotniczych z wykorzystaniem sztucznej inteligencji.

## 🚀 Nowe Funkcjonalności (v2.0)

### ✅ **Bezpieczeństwo**
- 🔐 Zmienne środowiskowe dla kluczy API
- 🛡️ Rate limiting (200 requestów/dzień, 50/godzinę)
- 🔒 Walidacja danych wejściowych
- 🛡️ Health checks

### ⚡ **Wydajność**
- 🚀 Cache'owanie Redis
- 📊 Metryki Prometheus
- 🔄 Lazy loading warstw
- ⚡ Zoptymalizowane requesty API

### 🧪 **Jakość Kodu**
- ✅ Testy jednostkowe
- 📝 Systematyczne logowanie
- 🔍 Monitoring i diagnostyka
- 🐳 Docker support

### 🎯 **UX/UI**
- 📱 Responsywny design
- ⚡ Loading states
- 🚨 Obsługa błędów
- 🎨 Nowoczesny interfejs

## 📋 Wymagania

- Python 3.11+
- Redis (opcjonalne)
- WeatherAPI.com API key
- Mapbox Access Token

## 🛠️ Instalacja

### 1. Klonowanie repozytorium
```bash
git clone <repository-url>
cd dokumentacja
```

### 2. Instalacja zależności
```bash
pip install -r requirements.txt
```

### 3. Konfiguracja zmiennych środowiskowych
```bash
cp env.example .env
# Edytuj .env i dodaj swoje klucze API
```

### 4. Uruchomienie z Docker (zalecane)
```bash
docker-compose up -d
```

### 5. Uruchomienie lokalnie
```bash
python run.py
```

## 🔧 Konfiguracja

### Zmienne środowiskowe (.env)
```env
# API Keys
WEATHERAPI_KEY=your_weatherapi_key_here
MAPBOX_ACCESS_TOKEN=your_mapbox_token_here

# Server settings
DEBUG=True
HOST=0.0.0.0
PORT=5000

# Redis settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Rate limiting
RATE_LIMIT_DAILY=200 per day
RATE_LIMIT_HOURLY=50 per hour
```

## 🧪 Testy

```bash
python test_app.py
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:5000/health
```

### Metryki Prometheus
```bash
curl http://localhost:5000/metrics
```

## 🐳 Docker

### Budowanie obrazu
```bash
docker build -t prognoza-przed-lotem .
```

### Uruchomienie z docker-compose
```bash
docker-compose up -d
```

### Sprawdzenie logów
```bash
docker-compose logs -f app
```

## 🔍 Diagnostyka

### Sprawdzenie stanu aplikacji
```bash
# Health check
curl http://localhost:5000/health

# Sprawdzenie Redis
redis-cli ping

# Sprawdzenie logów
docker-compose logs app
```

### Debugowanie
```bash
# Włącz tryb debug
export DEBUG=True

# Sprawdź metryki
curl http://localhost:5000/metrics
```

## 📈 Metryki i Monitoring

Aplikacja zawiera wbudowane metryki Prometheus:

- **HTTP Requests Total** - liczba requestów
- **HTTP Request Duration** - czas odpowiedzi
- **Rate Limiting** - limity requestów
- **Cache Hit Rate** - skuteczność cache'owania

## 🛡️ Bezpieczeństwo

### Rate Limiting
- 200 requestów dziennie
- 50 requestów na godzinę
- Konfigurowalne limity

### Walidacja
- Walidacja danych wejściowych
- Sanityzacja parametrów
- Obsługa błędów API

### Monitoring
- Health checks
- Logowanie błędów
- Metryki wydajności

## 🚀 Wydajność

### Cache'owanie
- Redis cache dla requestów API
- LRU cache dla często używanych danych
- TTL dla cache'owanych danych

### Optymalizacje
- Lazy loading warstw
- Kompresja odpowiedzi
- Pooling połączeń

## 📱 Funkcjonalności

### 🌤️ Prognozy Pogodowe
- Aktualna pogoda
- Prognoza 7-dniowa
- Szczegółowe dane meteorologiczne

### 🗺️ Mapy Interaktywne
- Mapbox GL JS
- Warstwy pogodowe
- Animacje 3D

### ✈️ Analiza Tras Lotniczych
- Analiza warunków lotu
- Rekomendacje
- Ostrzeżenia

### 🎨 Interfejs Użytkownika
- Responsywny design
- Nowoczesny UI
- Intuicyjna nawigacja

## 🔧 API Endpoints

### Podstawowe
- `GET /` - Strona główna
- `GET /ai_preflight` - Główna aplikacja
- `GET /health` - Health check

### Pogoda
- `GET /api/weather/current` - Aktualna pogoda
- `GET /api/weather/forecast` - Prognoza 7-dniowa
- `GET /api/config` - Konfiguracja

### Analiza Tras
- `POST /api/analyze_flight_route` - Analiza trasy lotu

### Warstwy Map
- `GET /api/weather/layers/*` - Warstwy pogodowe
- `GET /api/weather/mts/*` - Mapbox Tiling Service

## 📊 Struktura Projektu

```
dokumentacja/
├── app.py                 # Główna aplikacja Flask
├── config.py              # Konfiguracja
├── run.py                 # Entry point
├── requirements.txt       # Zależności Python
├── test_app.py           # Testy jednostkowe
├── Dockerfile            # Docker image
├── docker-compose.yml    # Docker orchestration
├── env.example           # Przykład zmiennych środowiskowych
├── static/               # Pliki statyczne
│   ├── css/
│   ├── js/
│   └── images/
├── templates/            # Szablony HTML
└── weather_tiles_cache/  # Cache dla tile'ów
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 Licencja

MIT License

## 🆘 Support

W przypadku problemów:

1. Sprawdź logi: `docker-compose logs app`
2. Sprawdź health check: `curl http://localhost:5000/health`
3. Sprawdź konfigurację: `cat .env`
4. Uruchom testy: `python test_app.py`

## 🔄 Changelog

### v2.0.0
- ✅ Dodano cache'owanie Redis
- ✅ Dodano rate limiting
- ✅ Dodano testy jednostkowe
- ✅ Dodano Docker support
- ✅ Dodano monitoring
- ✅ Poprawiono bezpieczeństwo
- ✅ Zoptymalizowano wydajność

### v1.0.0
- ✅ Podstawowa funkcjonalność
- ✅ Integracja z WeatherAPI.com
- ✅ Mapbox GL JS
- ✅ Analiza tras lotniczych
