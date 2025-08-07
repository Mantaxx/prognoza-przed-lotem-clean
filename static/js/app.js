/* =================================================================
   app.js - WERSJA OSTATECZNA
   ================================================================= */

// 1. Zmienna globalna, która będzie przechowywać naszą mapę
let map;
let activeLayers = new Set();

// 2. Definicje warstw pogodowych
const weatherLayers = [
    { id: 'temperature', name: '🌡️ Temperatura (MTS)', icon: '🌡️' },
    { id: 'wind', name: '💨 Wiatr (MTS)', icon: '💨' },
    { id: 'wind-vectors', name: '➡️ Wektory wiatru', icon: '➡️' },
    { id: 'precipitation', name: '🌧️ Opady', icon: '🌧️' },
    { id: 'radar', name: '📡 Radar pogodowy', icon: '📡' },
    { id: 'rain-animation', name: '🌧️ Animowany deszcz', icon: '🌧️' },
    { id: 'snow-animation', name: '❄️ Animowany śnieg', icon: '❄️' },
    { id: 'clouds', name: '☁️ Zachmurzenie', icon: '☁️' },
    { id: 'satellite', name: '🛰️ Satelita', icon: '🛰️' },
    { id: 'pressure', name: '📊 Ciśnienie', icon: '📊' },
    { id: 'humidity', name: '💧 Wilgotność', icon: '💧' },
    { id: 'visibility', name: '👁️ Widoczność', icon: '👁️' },
    { id: 'temperature-mts', name: '🌡️ Temperatura MTS (raster-array)', icon: '🌡️' },
    { id: 'wind-mts', name: '💨 Wiatr MTS (raster-array)', icon: '💨' },
    { id: 'temperature-animation', name: '🌡️ Animacja temperatury', icon: '🌡️' },
    { id: 'wind-animation', name: '💨 Animacja wiatru', icon: '💨' },
    { id: '3d-buildings', name: '🏢 Budynki 3D', icon: '🏢' },
    { id: '3d-terrain', name: '🏔️ Teren 3D', icon: '🏔️' },
    { id: '3d-weather', name: '🌤️ Pogoda 3D', icon: '🌤️' },
    { id: '3d-animations', name: '🎬 Animacje 3D', icon: '🎬' }
];

// 3. Główny punkt startowy aplikacji
document.addEventListener('DOMContentLoaded', initApp);

/**
 * Główna funkcja uruchamiająca całą aplikację.
 */
function initApp() {
    console.log('🚀 Aplikacja startuje, wywołuję initializeMap...');
    initializeMap();
    createLayerControls();
}

/**
 * Tworzy kontrolki warstw dynamicznie
 */
function createLayerControls() {
    const weatherPanel = document.querySelector('.weather-panel .panel-content');
    if (!weatherPanel) return;

    // Znajdź sekcję z podstawowymi warstwami
    const basicLayersSection = weatherPanel.querySelector('h4');
    if (!basicLayersSection) return;

    // Usuń istniejące kontrolki
    const existingControls = weatherPanel.querySelectorAll('.layer-control');
    existingControls.forEach(control => control.remove());

    // Dodaj podstawowe warstwy
    const basicLayers = weatherLayers.slice(0, 12);
    basicLayers.forEach(layer => {
        const control = document.createElement('div');
        control.className = 'layer-control';
        control.setAttribute('data-layer', layer.id);
        control.textContent = layer.name;
        weatherPanel.appendChild(control);
    });

    // Dodaj zaawansowane warstwy MTS
    const mtsHeader = document.createElement('h4');
    mtsHeader.textContent = '🔬 Zaawansowane warstwy MTS:';
    weatherPanel.appendChild(mtsHeader);

    const mtsLayers = weatherLayers.slice(12, 16);
    mtsLayers.forEach(layer => {
        const control = document.createElement('div');
        control.className = 'layer-control';
        control.setAttribute('data-layer', layer.id);
        control.textContent = layer.name;
        weatherPanel.appendChild(control);
    });

    // Dodaj warstwy 3D
    const threeDHeader = document.createElement('h4');
    threeDHeader.textContent = '🏗️ Warstwy 3D:';
    weatherPanel.appendChild(threeDHeader);

    const threeDLayers = weatherLayers.slice(16);
    threeDLayers.forEach(layer => {
        const control = document.createElement('div');
        control.className = 'layer-control';
        control.setAttribute('data-layer', layer.id);
        control.textContent = layer.name;
        weatherPanel.appendChild(control);
    });

    // Dodaj event listenery do nowych kontrolek
    initializeControls();
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

        // Różne typy warstw na podstawie layerId
        const layerConfig = getLayerConfig(layerId);
        map.addLayer(layerConfig);

        activeLayers.add(layerId);
        console.log(`✅ Dodano warstwę ${layerId}`);
    } catch (error) {
        console.error(`Nie udało się dodać warstwy ${layerId}:`, error);
    }
}

/**
 * Zwraca konfigurację warstwy na podstawie jej typu
 * @param {string} layerId - ID warstwy
 * @returns {Object} Konfiguracja warstwy Mapbox
 */
function getLayerConfig(layerId) {
    const baseConfig = {
        id: layerId,
        source: layerId
    };

    // Różne typy warstw na podstawie ID
    if (layerId.includes('temperature')) {
        return {
            ...baseConfig,
            type: 'heatmap',
            paint: {
                'heatmap-weight': [
                    'interpolate',
                    ['linear'],
                    ['get', 'temperature'],
                    0, 0,
                    30, 1
                ],
                'heatmap-intensity': 1,
                'heatmap-color': [
                    'interpolate',
                    ['linear'],
                    ['heatmap-density'],
                    0, 'rgba(0, 0, 255, 0)',
                    0.5, 'rgba(0, 255, 0, 0.5)',
                    1, 'rgba(255, 0, 0, 1)'
                ],
                'heatmap-radius': 30
            }
        };
    } else if (layerId.includes('wind')) {
        return {
            ...baseConfig,
            type: 'symbol',
            layout: {
                'icon-image': 'arrow',
                'icon-size': 0.5,
                'icon-rotate': ['get', 'wind_direction']
            },
            paint: {
                'icon-color': [
                    'interpolate',
                    ['linear'],
                    ['get', 'wind_speed'],
                    0, '#00ff00',
                    50, '#ff0000'
                ]
            }
        };
    } else {
        // Domyślna konfiguracja dla innych warstw
        return {
            ...baseConfig,
            type: 'circle',
            paint: {
                'circle-radius': 10,
                'circle-color': '#FF5733',
                'circle-stroke-width': 1,
                'circle-stroke-color': '#FFFFFF'
            }
        };
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