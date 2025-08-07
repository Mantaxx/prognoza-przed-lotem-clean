#!/usr/bin/env python3
"""
Production Weather Tile Server - Uses real WeatherAPI.com API
Replace WEATHERAPI_KEY with your actual API key
"""

import os
import math
import json
import requests
from flask import Flask, send_file, jsonify, request
from flask_cors import CORS
from PIL import Image, ImageDraw
import io
import numpy as np
from datetime import datetime, timedelta
import config

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration - Your WeatherAPI.com API Key
WEATHERAPI_KEY = config.WEATHERAPI_KEY  # Your API key from config.py
TILE_SIZE = 256
CACHE_DIR = "weather_tiles_cache"
CACHE_TIMEOUT = 3600  # 1 hour cache

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def num2deg(xtile, ytile, zoom):
    """Convert tile numbers to lat/lon"""
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def get_weather_data(lat, lon):
    """Fetch real weather data from WeatherAPI.com API"""
    try:
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': f"{lat},{lon}",
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Weather API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Weather API request failed: {e}")
        return None

def temperature_to_color(temp_celsius):
    """Convert temperature to color (blue=cold, red=hot)"""
    normalized = max(0, min(1, (temp_celsius + 40) / 90))
    
    if normalized < 0.25:
        ratio = normalized / 0.25
        r = 0
        g = int(ratio * 255)
        b = 255
    elif normalized < 0.5:
        ratio = (normalized - 0.25) / 0.25
        r = 0
        g = 255
        b = int(255 * (1 - ratio))
    elif normalized < 0.75:
        ratio = (normalized - 0.5) / 0.25
        r = int(ratio * 255)
        g = 255
        b = 0
    else:
        ratio = (normalized - 0.75) / 0.25
        r = 255
        g = int(255 * (1 - ratio))
        b = 0
    
    return (r, g, b, 128)

def wind_speed_to_color(wind_speed_ms):
    """Convert wind speed to color intensity"""
    normalized = max(0, min(1, wind_speed_ms / 30))
    r = int(normalized * 255)
    g = int((1 - normalized) * 255)
    b = 0
    return (r, g, b, 128)

def precipitation_to_color(precipitation_mm):
    """Convert precipitation to blue color intensity"""
    normalized = max(0, min(1, precipitation_mm / 10))
    r = 0
    g = 0
    b = 255
    alpha = int(normalized * 255)
    return (r, g, b, alpha)

def generate_weather_tile(layer_type, z, x, y):
    """Generate weather tile with real data"""
    lat_north, lon_west = num2deg(x, y, z)
    lat_south, lon_east = num2deg(x + 1, y + 1, z)
    
    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Sample points across the tile
    grid_size = 8 if z > 6 else 4
    
    for i in range(grid_size):
        for j in range(grid_size):
            lat = lat_north + (lat_south - lat_north) * i / (grid_size - 1)
            lon = lon_west + (lon_east - lon_west) * j / (grid_size - 1)
            
            weather_data = get_weather_data(lat, lon)
            
            if weather_data:
                px = int(j * TILE_SIZE / (grid_size - 1))
                py = int(i * TILE_SIZE / (grid_size - 1))
                
                color = None
                
                if layer_type == 'temperature':
                    temp = weather_data.get('current', {}).get('temp_c', 0)
                    color = temperature_to_color(temp)
                
                elif layer_type == 'wind':
                    wind_speed = weather_data.get('current', {}).get('wind_kph', 0) / 3.6  # Convert km/h to m/s
                    color = wind_speed_to_color(wind_speed)
                
                elif layer_type == 'precipitation':
                    precip_mm = weather_data.get('current', {}).get('precip_mm', 0)
                    color = precipitation_to_color(precip_mm)
                
                elif layer_type == 'pressure':
                    pressure = weather_data.get('current', {}).get('pressure_mb', 1013)
                    normalized = max(0, min(1, (pressure - 980) / 60))
                    color = (int(normalized * 255), 0, int((1-normalized) * 255), 128)
                
                elif layer_type == 'humidity':
                    humidity = weather_data.get('current', {}).get('humidity', 50)
                    normalized = humidity / 100
                    color = (0, int(normalized * 255), 255, 128)
                
                elif layer_type == 'clouds':
                    clouds = weather_data.get('current', {}).get('cloud', 0)
                    alpha = int(clouds * 255 / 100)
                    color = (255, 255, 255, alpha)
                
                if color:
                    cell_size = TILE_SIZE // grid_size
                    x1 = j * cell_size
                    y1 = i * cell_size
                    x2 = x1 + cell_size
                    y2 = y1 + cell_size
                    draw.rectangle([x1, y1, x2, y2], fill=color)
    
    return img

@app.route('/api/weather/<layer_type>/<int:z>/<int:x>/<int:y>.png')
def weather_tile(layer_type, z, x, y):
    """Serve weather tile with caching"""
    try:
        cache_path = os.path.join(CACHE_DIR, f"{layer_type}_{z}_{x}_{y}.png")
        
        # Check cache
        if os.path.exists(cache_path):
            cache_age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))).seconds
            if cache_age < CACHE_TIMEOUT:
                return send_file(cache_path, mimetype='image/png')
        
        print(f"🌦️ Generating real weather tile: {layer_type} {z}/{x}/{y}")
        img = generate_weather_tile(layer_type, z, x, y)
        img.save(cache_path, 'PNG')
        
        return send_file(cache_path, mimetype='image/png')
        
    except Exception as e:
        print(f"❌ Error generating tile {layer_type} {z}/{x}/{y}: {e}")
        img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return send_file(img_buffer, mimetype='image/png')

@app.route('/api/weather/wind-vectors')
def wind_vectors():
    """Serve real wind vector data"""
    try:
        bounds = request.args.get('bounds', '14,49,24,55')
        bbox = [float(x) for x in bounds.split(',')]
        
        vectors = []
        for lat in range(int(bbox[1]), int(bbox[3]), 2):
            for lon in range(int(bbox[0]), int(bbox[2]), 2):
                weather_data = get_weather_data(lat, lon)
                if weather_data and 'current' in weather_data:
                    current = weather_data['current']
                    vectors.append({
                        'lat': lat,
                        'lon': lon,
                        'speed': current.get('wind_kph', 0) / 3.6,  # Convert km/h to m/s
                        'direction': current.get('wind_degree', 0)
                    })
        
        return jsonify({'vectors': vectors})
        
    except Exception as e:
        print(f"❌ Error generating wind vectors: {e}")
        return jsonify({'vectors': []})

@app.route('/api/config')
def get_config():
    """API configuration endpoint"""
    return jsonify({
        'status': 'ok',
        'version': '1.0',
        'message': 'Production Weather Tile Server',
        'weather_layers': [
            'temperature', 'wind', 'precipitation', 'pressure', 
            'humidity', 'clouds', 'radar', 'satellite'
        ]
    })

@app.route('/api/weather/current')
def current_weather():
    """Real current weather"""
    lat = request.args.get('lat', 52.2297)
    lon = request.args.get('lon', 21.0122)
    
    weather_data = get_weather_data(float(lat), float(lon))
    if weather_data:
        return jsonify(weather_data)
    else:
        return jsonify({'error': 'Weather data not available'}), 500

@app.route('/api/weather/forecast')
def forecast():
    """Real weather forecast"""
    try:
        url = "http://api.weatherapi.com/v1/forecast.json"
        params = {
            'key': WEATHERAPI_KEY,
            'q': 'Warsaw',
            'days': 7,
            'aqi': 'no'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Forecast not available'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Server status"""
    return jsonify({
        'status': '🌦️ Production Weather Tile Server Running',
        'message': 'Using real WeatherAPI.com API data',
        'endpoints': [
            '/api/weather/<layer>/<z>/<x>/<y>.png - Weather tiles',
            '/api/weather/wind-vectors - Wind vector data',
            '/api/config - Server configuration',
            '/api/weather/current - Current weather',
            '/api/weather/forecast - Weather forecast'
        ]
    })

if __name__ == '__main__':
    print("🌦️ Starting Production Weather Tile Server...")
    print("📝 Using real WeatherAPI.com API data")
    print("🔑 API Key configured: " + WEATHERAPI_KEY[:10] + "...")
    print("🗺️ Tile endpoint: /api/weather/<layer>/<z>/<x>/<y>.png")
    app.run(host='0.0.0.0', port=5001, debug=True) 