import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(key, default: bool):
    return os.getenv(key, str(default)).lower() in ('true', '1', 't', 'y', 'yes', 'yeah', 'yep', 'yup', 'certainly')


DISCORD_TOKEN: str = os.getenv('DISCORD_TOKEN')
NEXUS_API_KEY: str = os.getenv('NEXUS_API_KEY')
DEBUG: bool = _get_bool("DEBUG", False)
DECOMPILE_THUNDERSTORE_MODS: bool = _get_bool("DECOMPILE_THUNDERSTORE_MODS", False)
