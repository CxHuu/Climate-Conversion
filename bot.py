import discord
import os
import re
import requests
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# ================= KEEP ALIVE ================= #

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# ================= ENV ================= #

TOKEN = os.getenv("TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

if not TOKEN:
    raise RuntimeError("TOKEN not set.")

# ================= DISCORD SETUP ================= #

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# FINAL regex (supports -21c, -21 C, -21°C etc.)
temp_pattern = re.compile(
    r"(?<!\w)(-?\d+(?:\.\d+)?)\s?°?\s?(C|F|K)(?!\w)",
    re.IGNORECASE
)

# Prevent duplicate processing
processed_messages = set()

# ================= READY ================= #

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

# ================= MESSAGE HANDLER ================= #

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Prevent double processing (important fix)
    if message.id in processed_messages:
        return
    processed_messages.add(message.id)

    content = message.content.strip()
    lower = content.lower()

    # WEATHER COMMAND
    if lower.startswith("!weather"):
        city = content[8:].strip()

        if not city:
            await message.channel.send("Example: `!weather London`")
            return

        if not WEATHER_API_KEY:
            return

        await send_weather(message, city)
        return

    # TIME COMMAND
    if lower.startswith("!time"):
        city = content[5:].strip()

        if not city:
            await message.channel.send("Example: `!time Tokyo`")
            return

        if not WEATHER_API_KEY:
            return

        await send_time(message, city)
        return

    # TEMPERATURE DETECTION
    matches = temp_pattern.findall(content)
    if matches:
        await send_temperature_conversion(message, matches)

# ================= TEMPERATURE ================= #

async def send_temperature_conversion(message, matches):
    embed = discord.Embed(
        title="🌡️ Temperature Conversion",
        color=discord.Color.orange()
    )

    for value_str, unit in matches:
        value = float(value_str)
        unit = unit.upper()

        if unit == "C":
            f = (value * 9/5) + 32
            k = value + 273.15
            result = f"{round(f,2)}°F | {round(k,2)}K"

        elif unit == "F":
            c = (value - 32) * 5/9
            k = c + 273.15
            result = f"{round(c,2)}°C | {round(k,2)}K"

        else:  # K
            c = value - 273.15
            f = (c * 9/5) + 32
            result = f"{round(c,2)}°C | {round(f,2)}°F"

        embed.add_field(
            name=f"{value_str}{unit}",
            value=result,
            inline=False
        )

    embed.set_footer(text=f"Requested by {message.author.display_name}")
    await message.channel.send(embed=embed)

# ================= WEATHER ================= #

async def send_weather(message, city):
    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": WEATHER_API_KEY.strip(),
        "units": "metric"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code != 200:
        await message.channel.send(f"API Error: {data.get('message', 'Unknown error')}")
        return

    temp = data["main"]["temp"]
    feels = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    description = data["weather"][0]["description"].title()
    country = data["sys"]["country"]
    wind = data["wind"]["speed"]
    pressure = data["main"]["pressure"]

    timezone_offset = data["timezone"]
    utc_now = datetime.utcnow()
    local_time = utc_now + timedelta(seconds=timezone_offset)

    formatted_time = local_time.strftime("%I:%M %p")
    utc_offset_hours = timezone_offset / 3600

    embed = discord.Embed(
        title=f"🌦️ Weather in {city.title()}, {country}",
        color=discord.Color.blue()
    )

    embed.add_field(name="Temperature", value=f"{temp}°C", inline=True)
    embed.add_field(name="Feels Like", value=f"{feels}°C", inline=True)
    embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
    embed.add_field(name="Wind Speed", value=f"{wind} m/s", inline=True)
    embed.add_field(name="Pressure", value=f"{pressure} hPa", inline=True)
    embed.add_field(name="Condition", value=description, inline=False)
    embed.add_field(
        name="Local Time",
        value=f"{formatted_time} (UTC {utc_offset_hours:+})",
        inline=False
    )

    await message.channel.send(embed=embed)

# ================= TIME ================= #

async def send_time(message, city):
    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": WEATHER_API_KEY.strip()
    }

    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code != 200:
        await message.channel.send(f"API Error: {data.get('message', 'Unknown error')}")
        return

    timezone_offset = data["timezone"]
    utc_now = datetime.utcnow()
    local_time = utc_now + timedelta(seconds=timezone_offset)

    formatted_time = local_time.strftime("%I:%M %p")
    utc_offset_hours = timezone_offset / 3600

    embed = discord.Embed(
        title=f"🕒 Local Time in {city.title()}",
        description=f"{formatted_time}\nUTC Offset: {utc_offset_hours:+}",
        color=discord.Color.purple()
    )

    await message.channel.send(embed=embed)

# ================= RUN ================= #

keep_alive()
client.run(TOKEN)
