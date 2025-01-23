# Weather-Aware Route Visualization

This project integrates real-time weather data with route planning to provide weather forecasts for key waypoints along a driving route. The application uses the OSRM API for route calculation and the Open-Meteo API for weather data. Results are displayed on an interactive map using Folium.

## Features

- **Route Calculation**: Fetches the shortest driving route using the OSRM API.
- **Weather Forecasting**: Retrieves hourly temperature data for waypoints along the route using Open-Meteo.
- **Interactive Visualization**: Displays the route and weather data on a Folium map with color-coded markers based on temperature (blue for freezing, green for mild, red for warm).

## Installation

1. Clone this repository:

2. Install required packages
pip install folium requests openmeteo-requests requests-cache pandas retry_requests numpy

## Usage

1. Set up start/end points:
```
start_lat, start_lon = 40.7128, -74.0060  # New York
end_lat, end_lon = 42.3601, -71.0589  # Boston
start_time = pd.to_datetime("2025-01-12 10:00:00").tz_localize('UTC')
```



