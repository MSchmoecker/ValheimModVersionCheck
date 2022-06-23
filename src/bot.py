import io
import discord
import os
import requests
import logging

from dotenv import load_dotenv
from readerwriterlock.rwlock import RWLockRead

from src import ModList, parse_local, compare_mods, fetch_errors
from discord.ext import commands, tasks

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
DEBUG: bool = os.getenv("DEBUG", 'False').lower() in ('true', '1', 't')


def run(file_lock: RWLockRead):
    client = discord.Client()
    modlist: ModList = ModList(file_lock)

    @tasks.loop(hours=1)
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
        errors = fetch_errors(log)

        logging.info(f"Send response with {len(response)} outdated mods and {len(errors)} errors")

        if len(response) == 0 and len(errors) == 0:
            await message.channel.send("No outdated or old mods found. No errors found.")
            return

        response_file_outdated_mods = make_file(response, "mods.txt")
        response_file_errors = make_file(errors, "errors.txt")
        response_files = [f for f in [response_file_outdated_mods, response_file_errors] if f is not None]

        msg = "Here you go! " \
              "A version might not exist if the mod is only available on NexusMods or the name is ambiguous."
        if len(response) == 0:
            msg += "No outdated or old mods found. "
        if len(errors) == 0:
            msg += "No errors found. "
        await message.channel.send(msg, files=response_files)

    def make_file(content, filename):
        if content is None or len(content) == 0:
            return None
        tmp = io.StringIO(content)
        return discord.File(tmp, filename=filename)

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
