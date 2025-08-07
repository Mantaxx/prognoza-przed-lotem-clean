# 🚀 Production Setup - Real Weather Data

## 📋 Przejście z Mock na Produkcję

### 1. **Pobierz klucz OpenWeatherMap API**

```bash
# Przejdź do: https://openweathermap.org/api
# Zarejestruj się i pobierz darmowy klucz API
# Darmowy plan: 1000 zapytań/dzień
```

### 2. **Zaktualizuj konfigurację**

W pliku `weather_tile_server_production.py`:
```python
OPENWEATHER_API_KEY = "your_actual_api_key_here"  # Zastąp swoim kluczem
```

### 3. **Uruchom serwer produkcyjny**

```bash
# Zatrzymaj mock serwer (Ctrl+C)
# Uruchom serwer produkcyjny
python weather_tile_server_production.py
```

### 4. **Sprawdź działanie**

```bash
# Test endpoint
curl http://127.0.0.1:5001/

# Test kafelka temperatury
curl http://127.0.0.1:5001/api/weather/temperature/6/32/21.png
```

## 🔧 Rozwiązywanie problemów

### **Konflikty portów**
Jeśli port 5000 jest zajęty:
```python
app.run(host='0.0.0.0', port=5002, debug=True)  # Zmień port
```

### **Konfiguracja frontendu**
Jeśli zmienisz port, zaktualizuj URL-e w `fixes.js`:
```javascript
url: 'http://127.0.0.1:5002/api/weather/temperature',  // Nowy port
```

### **Problemy z cache**
Wyczyść cache jeśli potrzebujesz:
```bash
rm -rf weather_tiles_cache/
```

## 📊 Porównanie Mock vs Produkcja

| Funkcja | Mock Server | Production Server |
|---------|-------------|-------------------|
| **Dane** | Demo/symulowane | Prawdziwe z OpenWeatherMap |
| **API calls** | Brak | 1000/dzień (darmowy plan) |
| **Cache** | Brak | 1 godzina |
| **Prędkość** | Szybkie | Zależy od API |
| **Dokładność** | Realistyczne wzorce | Prawdziwe dane |

## 🎯 Następne kroki

1. **Testuj z mock serwerem** - upewnij się, że wszystko działa
2. **Pobierz klucz API** - zarejestruj się na OpenWeatherMap
3. **Przełącz na produkcję** - użyj `weather_tile_server_production.py`
4. **Monitoruj API calls** - sprawdzaj limity
5. **Dodaj cache** - dla lepszej wydajności

## 🔍 Weryfikacja

Po uruchomieniu serwera produkcyjnego sprawdź:

```bash
# Status serwera
curl http://127.0.0.1:5001/

# Powinieneś zobaczyć:
{
  "status": "🌦️ Production Weather Tile Server Running",
  "message": "Using real OpenWeatherMap API data"
}
```

W konsoli przeglądarki:
```
🌦️ Generating real weather tile: temperature 6/32/21
✅ Warstwa temperature dodana pomyślnie
```

## ⚠️ Uwagi produkcyjne

- **Limity API**: OpenWeatherMap darmowy plan = 1000 zapytań/dzień
- **Cache**: Implementuj cache dla lepszej wydajności
- **Monitoring**: Monitoruj liczbę API calls
- **Backup**: Miej mock serwer jako backup

## 🎉 Gotowe!

Twoja aplikacja pogodowa jest teraz gotowa do produkcji z prawdziwymi danymi pogodowymi! 