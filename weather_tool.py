from langchain.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the current weather for a given location.

    Args:
        location: The city and state, e.g. San Francisco, CA
    """
    # Mock weather data - in a real implementation, call a weather API
    weather_data = {
        "San Francisco, CA": "Sunny, 72°F",
        "New York, NY": "Cloudy, 68°F",
        "Los Angeles, CA": "Clear, 78°F",
    }
    return weather_data.get(location, f"Weather data not available for {location}. Assuming it's nice out!")