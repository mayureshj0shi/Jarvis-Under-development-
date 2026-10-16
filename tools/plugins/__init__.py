from tools.plugins import weather as weather_plugin
from tools.registry import TOOLS

TOOLS["weather"] = {
    "func": weather_plugin.get_weather,
    "description": (
        "Get current weather for a city (free, no API key). "
        "args: {\"city\": \"<city>\"}"
    ),
}
