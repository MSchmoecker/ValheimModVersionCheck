import uvicorn
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from src import ModList, env, schemas
from src.threaded_uvicorn import ThreadedUvicorn


def run(modlist: ModList):
    app = FastAPI(root_path=env.API_ROOT_PATH)

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.get("/experimental/thunderstore-mods", response_model=schemas.ModList, tags=["deprecated"], deprecated=True)
    @app.get("/experimental/thunderstore-mods/{community}", response_model=schemas.ModList)
    def thunderstore_mods(community: str = "valheim"):
        return modlist.get_decompiled_mods(community.strip().lower())

    @app.get("/experimental/prepared-mods", response_model=schemas.BepInExModList, tags=["deprecated"], deprecated=True)
    @app.get("/experimental/prepared-mods/{community}", response_model=schemas.BepInExModList)
    def prepared_mods(community: str = "valheim"):
        """
            See <a href="https://github.com/MSchmoecker/ValheimModVersionCheck/blob/master/src/modnames.py">Github</a>
            for the cleanup function used to generate the dictionary keys.
        """

        return modlist.get_online_mods(community.strip().lower())

    ThreadedUvicorn(uvicorn.Config(app, host="0.0.0.0", port=env.API_PORT, root_path=env.API_ROOT_PATH)).start()
