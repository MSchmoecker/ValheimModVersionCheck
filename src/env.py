import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(key, default: bool):
    return os.getenv(key, str(default)).lower() in ('true', '1', 't', 'y', 'yes', 'yeah', 'yep', 'yup', 'certainly')


def _get_int(key, default: int):
    try:
        return int(os.getenv(key))
    except:
        return default


DISCORD_TOKEN: str = os.getenv('DISCORD_TOKEN')
NEXUS_API_KEY: str = os.getenv('NEXUS_API_KEY')
DEBUG: bool = _get_bool("DEBUG", False)
DECOMPILE_THUNDERSTORE_MODS: bool = _get_bool("DECOMPILE_THUNDERSTORE_MODS", False)
API_PORT: int = _get_int('API_PORT', 8000)
API_ROOT_PATH: str = os.getenv('API_ROOT_PATH') or "/"
