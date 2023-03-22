import datetime
import functools
import io
import json
import os
import time

import discord
import requests
import logging

from discord import Message
from discord.ext import tasks

from readerwriterlock.rwlock import RWLockRead

import app_version
from src import ModList, parse_local, compare_mods, fetch_errors, env, merge_errors
from typing import Optional, List


def run(file_lock: RWLockRead):
    logging.info(f"Starting Valheim Version Check {app_version.app_version}")
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
    async def on_message(message: Message):
        if message.author == client.user:
            return

        if env.DEBUG != (hasattr(message.channel, 'name') and message.channel.name == 'vmvc-debug-test'):
            return

        content: str = message.content

        if content == "!checkmods":
            logging.info("")
            logging.info("Got request !checkmods")

            logs = await get_logs(message, "!checkmods")
            if logs is not None:
                await on_checkmods(message, message.reference, logs, False)
            return

        if content == "!modlist":
            logging.info("")
            logging.info("Got request !modlist")

            logs = await get_logs(message, "!modlist")

            if logs is not None:
                await on_modlist(message, logs)
            return

        if content.startswith("!find faulty"):
            await send_detect_mods_instructions(message)

        if content.startswith("!thunderstore mods"):
            query = content[len("!thunderstore mods "):]
            logging.info("")
            logging.info(f"Got request !indexed mods with query: {query}")

            await send_indexed_mods(message, query)
            return

        if content.startswith("!postlog") or content.startswith("!post log"):
            await send_post_log_instructions(message)
            return

        logs = await _get_logs_from_attachment(message, message.attachments, True)
        if logs is not None:
            await on_checkmods(message, message, logs, True)

    async def send_indexed_mods(message, query):
        mods = modlist.get_decompiled_mods()

        if len(query) > 0:
            query = query.lower()
            result: dict = {}

            for mod_key in mods.keys():
                mod: dict = mods[mod_key]

                if query in mod["online_name"].lower():
                    result[mod_key] = mod
                    continue

                if any(query in m.lower() or query in mod["mods"][m]["name"].lower() for m in mod["mods"]):
                    result[mod_key] = mod
                    continue

            mods = result

        msg = "This are the extracted mods from Thunderstore"
        response_decompiled_mods = make_file(json.dumps(mods, indent=4, sort_keys=True), "mods.json")

        await message.channel.send(msg, file=response_decompiled_mods)

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

            response = compare_mods(mods_local, modlist.get_online_mods())
            errors = fetch_errors(log)

            time_watch = datetime.datetime.now()
            merged_errors = merge_errors(errors)
            logging.info(F"Merged errors in {datetime.datetime.now() - time_watch}")

            if silent_on_no_findings and len(response) == 0 and len(merged_errors) == 0:
                return

            logging.info(
                f"Send response with {len(response.splitlines())} outdated mods lines "
                f"and {len(merged_errors.splitlines())} errors lines")

            if len(response) == 0 and len(merged_errors) == 0:
                await message.channel.send("No outdated or old mods found. No errors found.",
                                           reference=original_message)
                return

            response_file_outdated_mods = make_file(response, "mods.txt")
            response_file_errors = make_file(merged_errors, "errors.txt")
            response_files = [response_file_outdated_mods, response_file_errors]
            response_files = [f for f in response_files if f is not None]

            msg = "Here you go! " \
                  "This is an automated check to quickly identify common problems. " \
                  "You can also DM me with log files.\n" \
                  "A flagged mod update may not exist if the mod is only available on NexusMods, " \
                  "the name is ambiguous or a beta version has been uploaded to Thunderstore.\n" \
                  "Take it with a grain of salt. "

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

    def get_modlist(mods_local):
        mod_list_text = ""

        for mod in sorted(mods_local.values(), key=lambda x: x["original_name"].lower()):
            mod_list_text += f'{mod["original_name"]} {mod["version"]}\n'

        return mod_list_text

    async def on_modlist(message, logs):
        for log in logs:
            logging.info("Parse attached file ... ")
            mods_local = parse_local(log, True)
            logging.info("done")

            response = get_modlist(mods_local)

            tmp = io.StringIO(response)
            response_file = discord.File(tmp, filename="mods.txt")
            msg = "Here you go!"
            await message.channel.send(msg, file=response_file)

    def get_user_message(key):
        path = os.path.join("data", "user_messages.json")

        if not os.path.exists(path):
            logging.warning(f"File {path} does not exist")
            return "Failed to load user messages"

        with open(path, "r+") as f:
            try:
                messages = json.load(f)
            except json.decoder.JSONDecodeError as e:
                logging.warning(f"Failed to load messages.json {e}")
                return "Failed to load user messages"

            if key in messages:
                return messages[key]
            else:
                return f"message is not configured in user messages"

    async def send_post_log_instructions(message: Message):
        await message.channel.send(get_user_message("post_log_instructions"))

    async def send_detect_mods_instructions(message):
        await message.channel.send(get_user_message("detect_mods_instructions"))

    async def wait_non_blocking(seconds):
        func = functools.partial(time.sleep, seconds)
        return await client.loop.run_in_executor(None, func)

    client.run(env.DISCORD_TOKEN)
