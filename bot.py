import io
import discord
import os
import requests

from dotenv import load_dotenv

from parse import parse_local, fetch_online, compare_mods

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    print()


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content != "!checkmods":
        return

    if message.reference is None:
        await message.channel.send("Answer to a logfile message")
        return

    if len(message.attachments) == 0:
        await message.channel.send("No file attached")
        return

    if len(message.attachments) > 0:
        await message.channel.send("Too many files")
        return

    replied_msg = await message.channel.fetch_message(message.reference.message_id)
    log = requests.get(replied_msg.attachments[0].url).text

    print("Parse attached file ... ", end="")
    mods_local = parse_local(log, True)
    print("done")

    response = compare_mods(mods_local)

    if len(response) == 0:
        await message.channel.send("No outdated or old mods found!")
        print()
        return

    tmp = io.StringIO(response)
    response_file = discord.File(tmp, filename="mods.txt")
    msg = "Here you go! " \
          "Versions are only read from the logfile and might not match the actual installed version"
    await message.channel.send(msg, file=response_file)
    print()


client.run(TOKEN)
