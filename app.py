import logging
import uvicorn

from src import bot, env, schemas, ModList
from readerwriterlock import rwlock
from fastapi import FastAPI

from src.threaded_uvicorn import ThreadedUvicorn

logging.basicConfig(format='[%(asctime)s %(levelname)-8s %(threadName)s] %(message)s', level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')

app = FastAPI()
file_lock = rwlock.RWLockRead()
modlist: ModList = ModList(file_lock)


@app.get("/experimental/thunderstore-mods", response_model=schemas.ModList)
def thunderstore_mods():
    return modlist.get_decompiled_mods()


@app.get("/experimental/prepared-mods", response_model=schemas.BepInExModList)
def prepared_mods():
    """
        See <a href="https://github.com/MSchmoecker/ValheimModVersionCheck/blob/master/src/modnames.py">Github</a>
        for the cleanup function used to generate the dictionary keys.
    """

    return modlist.get_online_mods()


if __name__ == '__main__':
    ThreadedUvicorn(uvicorn.Config(app, host="0.0.0.0", port=env.API_PORT)).start()
    bot.run(modlist)
