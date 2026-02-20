import discord
import os
import re
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

client = discord.Client(intents=intents)

temp_pattern = temp_pattern = re.compile(r'\b(-?\d+(?:\.\d+)?)\s?(C|F|K)\b', re.IGNORECASE)
converted_messages = set()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if temp_pattern.search(message.content):
        await message.add_reaction("🌡️")

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

        embed.add_field(
            name=f"{value}{unit}",
            value=result,
            inline=False
        )

    embed.set_footer(text=f"Requested by {user.display_name}")

    await message.channel.send(embed=embed)

    converted_messages.add(message.id)

    try:
        await reaction.remove(user)
    except:
        pass

keep_alive()
client.run(os.environ["TOKEN"])