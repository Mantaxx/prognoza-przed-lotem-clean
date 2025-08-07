/* =================================================================
   app.js - WERSJA OSTATECZNA
   ================================================================= */

// 1. Zmienna globalna, która będzie przechowywać naszą mapę
let map;
let activeLayers = new Set();

// 2. Główny punkt startowy aplikacji
document.addEventListener('DOMContentLoaded', initApp);

/**
 * Główna funkcja uruchamiająca całą aplikację.
 */
function initApp() {
    console.log('🚀 Aplikacja startuje, wywołuję initializeMap...');
    initializeMap();
}

/**
 * Tworzy i w pełni konfiguruje mapę Mapbox, zapewniając poprawną kolejność operacji.
 */
async function initializeMap() {
    try {
        mapboxgl.accessToken = await loadMapboxToken();
        console.log('🔑 Token załadowany.');

        // 3. TWORZENIE MAPY Z KLUCZOWYM PARAMETREM 'STYLE'
        //    Bez tego parametru, obiekt mapy jest niekompletny i bezużyteczny.
        map = new mapboxgl.Map({
            container: 'map',
            style: 'mapbox://styles/mapbox/streets-v11',
            center: [19.9, 50.0],
            zoom: 5
        });
        
        // 4. "ZŁOTY STANDARD": CZEKANIE NA ZAKOŃCZENIE ŁADOWANIA
        //    Cały kod, który ma modyfikować mapę, musi być wykonany wewnątrz tego bloku.
        map.on('load', () => {
            console.log('✅ Mapa w PEŁNI załadowana. Gotowa do akcji!');
            
            // DOPIERO TERAZ, GDY MAPA JEST GOTOWA, URUCHAMIAMY OBSŁUGĘ PRZYCISKÓW
            initializeControls();
        });

    } catch (error) {
        console.error('❌ KRYTYCZNY BŁĄD podczas tworzenia mapy:', error);
    }
}

/**
 * Dodaje listenery zdarzeń do wszystkich kontrolek warstw.
 */
function initializeControls() {
    const controls = document.querySelectorAll('.layer-control');
    console.log(`🎛️ Inicjalizuję ${controls.length} kontrolek...`);
    controls.forEach(control => {
        control.addEventListener('click', (e) => {
            // Pobieramy ID warstwy z atrybutu data-layer
            const layerId = e.currentTarget.dataset.layer;
            toggleLayer(layerId);
        });
    });
}

/**
 * Przełącza widoczność warstwy: pokazuje ją, jeśli jest ukryta, i ukrywa, jeśli jest widoczna.
 * @param {string} layerId - ID warstwy, np. 'temperature'.
 */
function toggleLayer(layerId) {
    if (!map) {
        console.error('Błąd w toggleLayer: Obiekt mapy nie istnieje!');
        return;
    }

    if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
        if (map.getSource(layerId)) {
            map.removeSource(layerId);
        }
        activeLayers.delete(layerId);
        console.log(`➖ Usunięto warstwę ${layerId}`);
    } else {
        addWeatherLayer(layerId);
    }
}

/**
 * Dodaje warstwę pogodową na mapę, pobierając dane z Twojego backendu.
 * @param {string} layerId - ID warstwy do dodania.
 */
async function addWeatherLayer(layerId) {
    if (!map) {
        console.error('Błąd w addWeatherLayer: Obiekt mapy nie istnieje!');
        return;
    }
    console.log(`➕ Dodaję warstwę dla ${layerId}...`);
    
    try {
        // Pobieramy dane z Twojego API w Pythonie
        const response = await fetch(`/api/weather/layers/${layerId}`);
        const geojsonData = await response.json();

        if (geojsonData.error) {
            throw new Error(geojsonData.error);
        }

        map.addSource(layerId, {
            type: 'geojson',
            data: geojsonData
        });

        // Przykładowa definicja warstwy - możesz ją dostosować
        map.addLayer({
            id: layerId,
            type: 'circle',
            source: layerId,
            paint: {
                'circle-radius': 10,
                'circle-color': '#FF5733',
                'circle-stroke-width': 1,
                'circle-stroke-color': '#FFFFFF'
            }
        });

        activeLayers.add(layerId);
        console.log(`✅ Dodano warstwę ${layerId}`);
    } catch (error) {
        console.error(`Nie udało się dodać warstwy ${layerId}:`, error);
    }
}


/**
 * Ładuje token Mapbox z Twojego API.
 */
async function loadMapboxToken() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        return config.mapbox_access_token;
    } catch (error) {
        console.error("Nie udało się załadować konfiguracji z /api/config", error);
        return null;
    }
} 