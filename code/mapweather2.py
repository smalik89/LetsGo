import folium
import requests
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from datetime import timedelta
import numpy as np

# Set up Open-Meteo API client with cache and retries
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# OSRM API URL
OSRM_URL = "http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"

def get_shortest_route(lat1, lon1, lat2, lon2):
    """Fetch shortest route and waypoints from OSRM."""
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&steps=true"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if "routes" in data and data["routes"]:
            return data["routes"][0]["legs"][0]["steps"], data["routes"][0]["legs"][0]["duration"]  # Steps and duration in seconds
        else:
            raise Exception("No routes found in the response.")
    else:
        raise Exception(f"Error fetching route data from OSRM: {response.content.decode()}")

def get_weather(lat, lon, target_time):
    """Fetch hourly weather data for a given latitude and longitude using Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "forecast_days": 1
    }
    response = requests.get(url, params=params).json()
    
    # Extract hourly data
    hourly = response['hourly']
    hourly_temperature_2m = np.array(hourly['temperature_2m'])
    hourly_time = pd.to_datetime(hourly['time']).tz_localize('UTC')  # Ensure it's in datetime format and timezone-aware

    # Ensure target_time is in UTC as well (convert if needed)
    if target_time.tzinfo is None:
        target_time = target_time.tz_localize('UTC')
    else:
        target_time = target_time.tz_convert('UTC')

    # Calculate the absolute differences between target_time and each hourly time
    time_differences = np.abs(hourly_time - target_time)  # Use np.abs() for array difference

    # Find the index of the smallest difference
    closest_time_idx = np.argmin(time_differences)  # Index with the smallest difference
    closest_temperature = hourly_temperature_2m[closest_time_idx]
    closest_time = hourly_time[closest_time_idx]  # Directly access the closest time

    return closest_temperature, closest_time

def get_weather_along_route(lat1, lon1, lat2, lon2, start_time):
    """Fetch the shortest route and get weather along the way."""
    steps, total_duration = get_shortest_route(lat1, lon1, lat2, lon2)
    weather_updates = []
    
    # Calculate the time intervals based on the duration of each step in the route
    current_time = start_time
    for step in steps:
        location = step["maneuver"]["location"]
        lat, lon = location[1], location[0]
        
        # Get the weather data for the estimated arrival time at this point
        step_duration_seconds = step["duration"]
        step_duration_minutes = step_duration_seconds / 60  # Convert to minutes
        current_time += timedelta(seconds=step_duration_seconds)
        temperature, arrival_time = get_weather(lat, lon, current_time)
        
        # Ensure arrival_time is in local time zone (UTC to local conversion if needed)
        arrival_time_local = current_time.tz_convert(start_time.tzinfo)  # Convert to the same timezone as start_time

        # Debugging: Print arrival_time and current_time
        print(f"Waypoint: {step['name'] or 'Unnamed Road'}, Arrival Time: {arrival_time_local}, Step Duration: {step_duration_minutes:.2f} minutes")
        
        weather_updates.append({
            "step": step["name"] or "Unnamed Road",
            "latitude": lat,
            "longitude": lon,
            "temperature": temperature * 9/5 + 32,  # Convert to Fahrenheit
            "time": arrival_time_local.strftime("%Y-%m-%d %H:%M:%S")  # Display the time
        })
    
    return weather_updates


def visualize_route_with_weather(weather_route, start_lat, start_lon):
    """Visualize the route and weather on a map."""
    # Create a folium map centered at the start location
    route_map = folium.Map(location=[start_lat, start_lon], zoom_start=12)
    
    # Add a marker for the start point
    folium.Marker([start_lat, start_lon], popup="Start").add_to(route_map)
    
    # List to store coordinates for drawing the line
    route_coords = []
    
    # Plot each weather update as a marker on the route
    for step in weather_route:
        lat = step["latitude"]
        lon = step["longitude"]
        temp = step["temperature"]
        
        # Create a popup with location, temperature, and time
        popup_content = f"Location: {step['step']}<br>Temperature: {temp:.2f}°F<br>Time: {step['time']}"
        
        # Create a colored circle marker based on temperature
        if temp < 32:  # Below freezing (32°F)
            color = "blue"
        elif temp >= 32 and temp <= 50:  # Mild temperature
            color = "green"
        else:  # Warm temperature
            color = "red"
        
        # Add circle marker for each weather update
        folium.CircleMarker(
            [lat, lon], 
            radius=8, 
            color=color, 
            fill=True, 
            fill_color=color, 
            fill_opacity=0.6, 
            popup=popup_content
        ).add_to(route_map)
        
        # Add the coordinate to the route path
        route_coords.append([lat, lon])

    # Draw a red line along the route
    folium.PolyLine(route_coords, color="red", weight=2.5, opacity=1).add_to(route_map)

    # Display the map
    return route_map

# Example Usage
start_lat, start_lon = 40.7128, -74.0060  # New York
end_lat, end_lon = 42.3601, -71.0589  # Boston
start_time = pd.to_datetime("2025-01-12 10:00:00").tz_localize('UTC')  # Start time at 10:00 AM on January 12, 2025

# Fetch the weather along the route
weather_route = get_weather_along_route(start_lat, start_lon, end_lat, end_lon, start_time)

# Visualize the route with weather data
route_map = visualize_route_with_weather(weather_route, start_lat, start_lon)

# Save the map to an HTML file
route_map.save("route_with_weather_times.html")
