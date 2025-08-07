# 🚀 Instrukcja Uruchomienia Aplikacji

## 📋 Wymagania

- Python 3.8 lub nowszy
- Przeglądarka internetowa z obsługą WebGL
- Połączenie internetowe

## 🔧 Instalacja

1. **Zainstaluj zależności:**

```bash
pip install -r requirements.txt
```

1. **Sprawdź konfigurację:**

   - Otwórz plik `config.py`
   - Upewnij się, że klucze API są poprawnie ustawione

## 🎯 Uruchomienie

### Sposób 1: Użyj pliku run.py (zalecane)

```bash
python run.py
```

### Sposób 2: Uruchom bezpośrednio app.py

```bash
python app.py
```

### Sposób 3: Użyj Flask CLI

```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

## 🌐 Dostęp do aplikacji

Po uruchomieniu aplikacja będzie dostępna pod adresami:

- **Strona główna:** <http://localhost:5000/>
- **Aplikacja AI:** <http://localhost:5000/ai_preflight>

## 🔍 Sprawdzenie działania

1. Otwórz przeglądarkę i przejdź do <http://localhost:5000/ai_preflight>
2. Sprawdź czy:

   - Mapa się ładuje (Mapbox)
   - Dane pogodowe są wyświetlane (OpenWeather API)
   - Wszystkie kontrolki działają

## 🐛 Rozwiązywanie problemów

### Mapa się nie ładuje

- Sprawdź czy token Mapbox jest poprawny w `config.py`
- Sprawdź połączenie internetowe
- Wyczyść cache przeglądarki

### Dane pogodowe nie ładują się

- Sprawdź czy klucz OpenWeather API jest poprawny
- Sprawdź limit zapytań API
- Sprawdź logi w konsoli przeglądarki (F12)

### Błąd "Module not found"

- Upewnij się, że zainstalowałeś wszystkie zależności: `pip install -r requirements.txt`

### Błąd portu

- Zmień port w `config.py` lub użyj innego portu
- Sprawdź czy port nie jest zajęty przez inną aplikację

## 📱 Testowanie na urządzeniach mobilnych

Aplikacja jest responsywna i działa na urządzeniach mobilnych. Aby przetestować:

1. Uruchom aplikację na komputerze
2. Znajdź adres IP komputera w sieci lokalnej
3. Na urządzeniu mobilnym otwórz: <http://[IP_KOMPUTERA]:5000/ai_preflight>

## 🔧 Konfiguracja zaawansowana

Możesz zmodyfikować ustawienia w pliku `config.py`:

- `DEBUG` - tryb debugowania
- `HOST` - adres hosta
- `PORT` - port serwera
- `DEFAULT_CENTER` - domyślne centrum mapy
- `DEFAULT_ZOOM` - domyślne przybliżenie
- `DEFAULT_PITCH` - domyślny kąt nachylenia

## 🛑 Zatrzymanie aplikacji

W terminalu naciśnij `Ctrl+C` aby zatrzymać serwer.

## 📊 Monitorowanie

Aplikacja loguje informacje do konsoli. Możesz monitorować:

- Żądania HTTP
- Błędy API
- Wydajność aplikacji
