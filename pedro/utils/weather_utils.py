import json
import logging
import typing as T
from typing import Any, Coroutine

import aiohttp
from asyncio import wait_for
from datetime import datetime

from geopy.geocoders import Nominatim

from pedro.brain.constants.constants import DAYS_OF_WEEK
from pedro.data_structures.bot_config import BotConfig


async def get_forecast(config: BotConfig, place: T.Optional[str], days: T.Optional[int]) -> str:
    if not place:
        place = "russia"
    if not days:
        days = 2
    elif isinstance(days, int) and days > 7:
        days = 7

    # Weather condition to icon mapping
    weather_icons = {
        'clear': '☀',  # Clear sky
        'clouds': '☁',  # Cloudy
        'rain': '☔',  # Rain
        'drizzle': '☔',  # Drizzle
        'thunderstorm': '⚡',  # Thunderstorm
        'snow': '❄',  # Snow
        'mist': '🌫',  # Mist
        'smoke': '🌫',  # Smoke
        'haze': '🌫',  # Haze
        'dust': '🌫',  # Dust
        'fog': '🌫',  # Fog
        'sand': '🌫',  # Sand
        'ash': '🌫',  # Ash
        'squall': '💨',  # Squall
        'tornado': '🌪',  # Tornado
    }

    try:
        lat, lon, location_str = None, None, None

        for _ in range(3):
            local = None
            try:
                local = await wait_for(
                    get_lat_lon(place),
                    timeout=450
                )
            except Exception as exc:
                logging.exception(exc)

            if isinstance(local, tuple) and len(local) == 3:
                lat, lon, location_str = local
                break

        if lat is None or lon is None:
            return "Não foi possível encontrar o local especificado."

        app_id = config.secrets.open_weather
        forecast_lines = [f"🌎 {location_str}"]

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.openweathermap.org/data/3.0/onecall?"
                                   f"cnt={days}&units=metric&lat={lat}&lon={lon}&lang=pt&appid={app_id}") as req:
                resp = json.loads(await req.text())

                if 'daily' in resp and isinstance(resp['daily'], list):
                    for i, day_data in enumerate(resp['daily'][:int(days)]):
                        # Get date in DD/MM format
                        date_obj = datetime.fromtimestamp(day_data['dt'])
                        date_str = date_obj.strftime("%d/%m")

                        # Get min and max temperatures
                        min_temp = round(day_data['temp']['min'])
                        max_temp = round(day_data['temp']['max'])

                        # Get weather condition and corresponding icon
                        weather_main = day_data['weather'][0]['main'].lower()
                        weather_icon = weather_icons.get(weather_main, '☁')

                        high_temp_icon = " 🔥" if max_temp > 31 else ""
                        ultra_high_temp_icon = "🔥" if max_temp > 35 else ""

                        # Get thermal sensation
                        feels_like = round(day_data['feels_like']['day'])

                        # Get day of week
                        day_of_week = DAYS_OF_WEEK[date_obj.weekday()]

                        # Format the forecast line
                        forecast_line = (
                            f"{date_str} ⬇{min_temp}º ⬆{max_temp}º {weather_icon}{high_temp_icon}{ultra_high_temp_icon} - "
                            f"{day_of_week} - 🌡️{feels_like}º"
                        )

                        forecast_lines.append(forecast_line)

                return "\n".join(forecast_lines)

    except Exception as exc:
        logging.exception(exc)

    return "Não encontrei o local."


async def get_lat_lon(place: str) -> tuple[Any, Any, str] | None:
    geolocator = Nominatim(
        user_agent="Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")

    try:
        location = geolocator.geocode(place, addressdetails=True)
        if location:
            # Extract city, state, country from address
            address = location.raw.get('address', {})
            city = address.get('city', address.get('town', address.get('village', address.get('municipality', ''))))
            state = address.get('state', '')
            country = address.get('country', '')
            suburb = address.get('suburb', '')

            # Format location string
            location_str = f"{city}"
            if state:
                location_str += f", {state}"
            if country:
                location_str += f", {country}"

            if suburb:
                location_str = f"{suburb}, {location_str}"

            return location.latitude, location.longitude, location_str
    except Exception as exc:
        logging.exception(exc)


def f_to_c(value: int) -> int:
    return round((value - 32) * 5 / 9)
