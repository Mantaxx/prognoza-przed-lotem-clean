#!/usr/bin/env python3
"""
Uruchomienie aplikacji Prognoza Przed Lotem
"""

import config
from app import app

if __name__ == '__main__':
    print("🌤️ Uruchamianie aplikacji Prognoza Przed Lotem...")
    print(f"📍 Serwer będzie dostępny pod adresem: http://localhost:{config.PORT}")
    print(f"🕊️ Główna aplikacja: http://localhost:{config.PORT}/ai_preflight")
    print("🛑 Aby zatrzymać serwer, naciśnij Ctrl+C")
    print("-" * 50)
    
    try:
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
    except KeyboardInterrupt:
        print("\n👋 Aplikacja została zatrzymana")
    except Exception as e:
        print(f"❌ Błąd podczas uruchamiania: {e}") 