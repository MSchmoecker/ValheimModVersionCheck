import io
import discord
import os
import requests
import logging

from dotenv import load_dotenv
from src import ModList, parse_local, compare_mods
from discord.ext import commands, tasks

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
DEBUG: bool = os.getenv("DEBUG", 'False').lower() in ('true', '1', 't')

logging.basicConfig(format='[%(asctime)s %(levelname)-8s] %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


def run():
    client = discord.Client()
    modlist: ModList = ModList()

    @tasks.loop(hours=24)
    async def fetch_mods():
        modlist.fetch_mods()

    fetch_mods.start()

    @client.event
    async def on_ready():
        logging.info(f'{client.user} has connected to Discord!')

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        if DEBUG != (hasattr(message.channel, 'name') and message.channel.name == 'vmvc-debug-test'):
            return

        if message.content == "!checkmods":
            logging.info("")
            logging.info("Got request !checkmods")

            log = await get_log(message, "!checkmods")

            if log is not None:
                await on_checkmods(message, log)

        if message.content == "!modlist":
            logging.info("")
            logging.info("Got request !modlist")

            log = await get_log(message, "!modlist")

            if log is not None:
                await on_modlist(message, log)

    async def get_log(message, command_name):
        if message.reference is None:
            logging.info("Message has no reference")
            await message.channel.send(f"Reply to an already posted logfile with {command_name}")
            return None

        replied_msg = await message.channel.fetch_message(message.reference.message_id)

        if len(replied_msg.attachments) == 0:
            logging.info("Message has no attachments")
            await message.channel.send("No file attached")
            return None

        if len(replied_msg.attachments) >= 2:
            logging.info("Message has too many attachments")
            await message.channel.send("Too many files")
            return None

        return requests.get(replied_msg.attachments[0].url).text

    async def on_checkmods(message, log):
        logging.info("Parse attached file ... ")
        mods_local = parse_local(log, True)
        logging.info("done")

        modlist.fetch_mods()
        response = compare_mods(mods_local, modlist.mods_online)

        logging.info(f"Send response with {len(response)} outdated mods")

        if len(response) == 0:
            await message.channel.send("No outdated or old mods found!")
            return

        tmp = io.StringIO(response)
        response_file = discord.File(tmp, filename="mods.txt")
        msg = "Here you go! " \
              "Versions are only read from the logfile and might not match the actual installed version"
        await message.channel.send(msg, file=response_file)

    async def on_modlist(message, log):
        logging.info("Parse attached file ... ")
        mods_local = parse_local(log, True)
        logging.info("done")

        response = ""

        for mod in sorted(mods_local.values(), key=lambda x: x["original_name"].lower()):
            response += f'{mod["original_name"]} {mod["version"]}\n'

        tmp = io.StringIO(response)
        response_file = discord.File(tmp, filename="mods.txt")
        msg = "Here you go!"
        await message.channel.send(msg, file=response_file)

        modlist.fetch_mods()

    client.run(TOKEN)
