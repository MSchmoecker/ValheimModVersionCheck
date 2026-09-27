import logging
import os
import shutil

import app_version
from src import bot, ModList, api, config, decompile
from src.mod import THUNDERSTORE
from readerwriterlock import rwlock

logging.basicConfig(
    format="[%(asctime)s %(levelname)-8s %(threadName)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

file_lock = rwlock.RWLockRead()
modlist: ModList = ModList(file_lock)


def move_file(old_path: str, new_path: str):
    if os.path.isfile(old_path):
        logging.info(f"Moving {old_path} to {new_path}")
        shutil.move(old_path, new_path)


def move_old_files():
    # the data folder used to hold a single game, which was always Valheim
    move_file(
        os.path.join("data", "decompiled_mods.json"),
        os.path.join("data", "valheim_decompiled_mods.json"),
    )
    move_file(
        os.path.join("data", "nexus_mods.json"),
        os.path.join("data", "valheim_nexus_mods.json"),
    )

    # decompiled mods are now stored per host, every previous file came from Thunderstore
    for game in config.get_games():
        if game.thunderstore:
            move_file(
                os.path.join("data", f"{game.thunderstore}_decompiled_mods.json"),
                decompile.mods_file_path(THUNDERSTORE, game.thunderstore),
            )


if __name__ == "__main__":
    logging.info(f"Starting Version Check {app_version.app_version}")

    move_old_files()

    for game in config.get_games():
        modlist.update_mod_list(game)

    api.run(modlist)
    bot.run(modlist)
