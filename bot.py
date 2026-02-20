import discord
import os
import re
import requests
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# ---------------- KEEP ALIVE ---------------- #

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ---------------- DISCORD SETUP ---------------- #

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

client = discord.Client(intents=intents)

temp_pattern = re.compile(r'\b(-?\d+(?:\.\d+)?)\s?(C|F|K)\b', re.IGNORECASE)
converted_messages = set()

# ---------------- READY ---------------- #

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

# ---------------- MESSAGE HANDLER ---------------- #

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # 🌡️ Auto react for temperature
    if temp_pattern.search(message.content):
        await message.add_reaction("🌡️")

    # 🌦️ Weather Command
    if message.content.startswith("!weather"):
        city = message.content.replace("!weather", "").strip()
        if not city:
            await message.channel.send("Example: `!weather London`")
            return

        await send_weather(message, city)

    # 🕒 Time Command
    if message.content.startswith("!time"):
        city = message.content.replace("!time", "").strip()
        if not city:
            await message.channel.send("Example: `!time Tokyo`")
            return

        await send_time(message, city)

# ---------------- REACTION HANDLER ---------------- #

@client.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if str(reaction.emoji) != "🌡️":
        return

    message = reaction.message

    if message.id in converted_messages:
        return

    matches = temp_pattern.findall(message.content)
    if not matches:
        return

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

        elif unit == "K":
            c = value - 273.15
            f = (c * 9/5) + 32
            result = f"{round(c,2)}°C | {round(f,2)}°F"

        embed.add_field(name=f"{value}{unit}", value=result, inline=False)

    embed.set_footer(text=f"Requested by {user.display_name}")

    await message.channel.send(embed=embed)
    converted_messages.add(message.id)

# ---------------- WEATHER FUNCTION ---------------- #

async def send_weather(message, city):
    api_key = os.environ["WEATHER_API_KEY"]
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    response = requests.get(url)
    if response.status_code != 200:
        await message.channel.send("City not found.")
        return

    data = response.json()

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
    embed.add_field(name="Local Time", value=f"{formatted_time} (UTC {utc_offset_hours:+})", inline=False)

    await message.channel.send(embed=embed)

# ---------------- TIME FUNCTION ---------------- #

async def send_time(message, city):
    api_key = os.environ["WEATHER_API_KEY"]
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"

    response = requests.get(url)
    if response.status_code != 200:
        await message.channel.send("City not found.")
        return

    data = response.json()

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

# ---------------- RUN ---------------- #

keep_alive()
client.run(os.environ["TOKEN"])
