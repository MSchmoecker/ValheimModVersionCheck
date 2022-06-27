import functools
import io
import time

import discord
import requests
import logging
from readerwriterlock.rwlock import RWLockRead
from src import ModList, parse_local, compare_mods, fetch_errors, env
from discord.ext import commands, tasks
from typing import Optional, List


def run(file_lock: RWLockRead):
    client = discord.Client()
    modlist: ModList = ModList(file_lock)
    modlist.update_mod_list()

    @tasks.loop(hours=1)
    async def fetch_mods():
        await wait_non_blocking(seconds=10)
        modlist.fetch_mods()

    fetch_mods.start()

    @client.event
    async def on_ready():
        logging.info(f'{client.user} has connected to Discord!')

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        if env.DEBUG != (hasattr(message.channel, 'name') and message.channel.name == 'vmvc-debug-test'):
            return

        if message.content == "!checkmods":
            logging.info("")
            logging.info("Got request !checkmods")

            logs = await get_logs(message, "!checkmods")
            if logs is not None:
                await on_checkmods(message, message.reference, logs, False)
            return

        if message.content == "!modlist":
            logging.info("")
            logging.info("Got request !modlist")

            logs = await get_logs(message, "!modlist")

            if logs is not None:
                await on_modlist(message, logs)
            return

        logs = await _get_logs_from_attachment(message, message.attachments, True)
        if logs is not None:
            await on_checkmods(message, message, logs, True)

    async def get_logs(message, command_name, silent=False) -> Optional[List[str]]:
        if message.reference is None:
            if not silent:
                logging.info("Message has no reference")
                await message.channel.send(f"Reply to an already posted logfile with {command_name}")
            return None

        replied_msg = await message.channel.fetch_message(message.reference.message_id)
        return await _get_logs_from_attachment(message, replied_msg.attachments, silent)

    async def _get_logs_from_attachment(message, attachments, silent) -> Optional[List[str]]:
        if len(attachments) == 0:
            if not silent:
                logging.info("Message has no attachments")
                await message.channel.send("No file attached")
            return None

        try:
            logs = []
            for attachment in attachments:
                r = requests.get(attachment.url)
                r.encoding = 'utf-8'
                log = r.text

                if log is None or type(log) is not str or len(log) == 0:
                    continue

                if not log.strip().startswith("[Message:   BepInEx]"):
                    continue

                logs.append(log)
            return logs
        except Exception as e:
            logging.exception(f"Failed to get log from attachment: {e}")
            return []

    async def on_checkmods(message, original_message, logs, silent_on_no_findings):
        if not silent_on_no_findings and len(logs) == 0:
            await message.channel.send("No logs found")
            return

        for log in logs:
            logging.info("Parse attached file ... ")
            mods_local = parse_local(log, True)
            logging.info("done")

            response = compare_mods(mods_local, modlist.get_online_mods())
            errors = fetch_errors(log)

            if silent_on_no_findings and len(response) == 0 and len(errors) == 0:
                return

            logging.info(
                f"Send response with {len(response.splitlines())} outdated mods and {len(errors.splitlines())} errors")

            if len(response) == 0 and len(errors) == 0:
                await message.channel.send("No outdated or old mods found. No errors found.",
                                           reference=original_message)
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
            await message.channel.send(msg, files=response_files, reference=original_message)

    def make_file(content, filename):
        if content is None or len(content) == 0:
            return None
        tmp = io.StringIO(content)
        return discord.File(tmp, filename=filename)

    async def on_modlist(message, logs):
        for log in logs:
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

    async def wait_non_blocking(seconds):
        func = functools.partial(time.sleep, seconds)
        return await client.loop.run_in_executor(None, func)

    client.run(env.DISCORD_TOKEN)
