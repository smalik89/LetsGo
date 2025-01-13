import requests
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

# Set up Open-Meteo API client with cache and retries
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# OSRM API URL
OSRM_URL = "http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"

def get_shortest_route(lat1, lon1, lat2, lon2):
    """Fetch shortest route and waypoints from OSRM."""
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&steps=true"
    print(f"Requesting route from OSRM: {url}")  # Debugging
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    # print(f"Response Status Code: {response.status_code}")
    # print(f"Response Headers: {response.headers}")
    # print(f"Response Content: {response.content}")
    
    if response.status_code == 200:
        data = response.json()
        if "routes" in data and data["routes"]:
            return data["routes"][0]["legs"][0]["steps"]  # Steps in the route
        else:
            raise Exception("No routes found in the response.")
    else:
        raise Exception(f"Error fetching route data from OSRM: {response.content.decode()}")

def get_weather(lat, lon):
    """Fetch hourly weather data for a given latitude and longitude using Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "forecast_days": 1
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]  # Process first response
    
    # Extract hourly data
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_data = {
        "time": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temperature_2m": hourly_temperature_2m
    }
    return pd.DataFrame(data=hourly_data)

def get_weather_along_route(lat1, lon1, lat2, lon2):
    """Fetch the shortest route and get weather along the way."""
    steps = get_shortest_route(lat1, lon1, lat2, lon2)
    weather_updates = []

    for step in steps:
        location = step["maneuver"]["location"]  # Extract coordinates
        lat, lon = location[1], location[0]
        
        # Fetch hourly weather data
        weather_df = get_weather(lat, lon)
        current_weather = weather_df.iloc[0]  # Get the first hour's weather
        
        weather_updates.append({
            "step": step["name"] or "Unnamed Road",
            "latitude": lat,
            "longitude": lon,
            "temperature": current_weather["temperature_2m"],
            "time": current_weather["time"]
        })

    return weather_updates

# Example Usage
start_lat, start_lon = 40.7128, -74.0060  # New York
end_lat, end_lon = 42.3601, -71.0589  # Boston

weather_route = get_weather_along_route(start_lat, start_lon, end_lat, end_lon)

# Display results
for i, weather in enumerate(weather_route):
    print(f"Step {i+1}:")
    print(f"  Location: {weather['step']} ({weather['latitude']:.2f}, {weather['longitude']:.2f})")
    print(f"  Temperature: {weather['temperature']}°C")
    print(f"  Time: {weather['time']}\n")
