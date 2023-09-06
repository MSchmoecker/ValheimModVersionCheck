import uvicorn
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from src import ModList, env, schemas
from src.threaded_uvicorn import ThreadedUvicorn


def run(modlist: ModList):
    app = FastAPI(root_path=env.API_ROOT_PATH)

    app.add_middleware(GZipMiddleware, minimum_size=1000)

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

    ThreadedUvicorn(uvicorn.Config(app, host="0.0.0.0", port=env.API_PORT, root_path=env.API_ROOT_PATH)).start()
