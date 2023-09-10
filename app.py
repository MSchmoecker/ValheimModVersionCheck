import logging
import os
import shutil

import app_version
from src import bot, ModList, api, config
from readerwriterlock import rwlock

logging.basicConfig(format='[%(asctime)s %(levelname)-8s %(threadName)s] %(message)s', level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')

file_lock = rwlock.RWLockRead()
modlist: ModList = ModList(file_lock)


def move_old_files():
    if os.path.isfile(os.path.join("data", "decompiled_mods.json")):
        shutil.move(os.path.join("data", "decompiled_mods.json"), os.path.join("data", "valheim_decompiled_mods.json"))
    if os.path.isfile(os.path.join("data", "nexus_mods.json")):
        shutil.move(os.path.join("data", "nexus_mods.json"), os.path.join("data", "valheim_nexus_mods.json"))


if __name__ == '__main__':
    logging.info(f"Starting Version Check {app_version.app_version}")

    move_old_files()

    for game in config.get_games():
        modlist.update_mod_list(game)

    api.run(modlist)
    bot.run(modlist)
