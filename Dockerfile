# Dockerfile dla aplikacji Prognoza Przed Lotem
FROM python:3.11-slim

# Ustawienie katalogu roboczego
WORKDIR /app

# Instalacja systemowych zależności
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Kopiowanie plików requirements
COPY requirements.txt .

# Instalacja zależności Python
RUN pip install --no-cache-dir -r requirements.txt

# Kopiowanie kodu aplikacji
COPY . .

# Utworzenie użytkownika nie-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Ekspozycja portu
EXPOSE 5000

# Zmienne środowiskowe
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Uruchomienie aplikacji
CMD ["python", "run.py"] 