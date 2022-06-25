import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.getenv('DISCORD_TOKEN')
NEXUS_API_KEY: str = os.getenv('NEXUS_API_KEY')
DEBUG: bool = os.getenv("DEBUG", 'False').lower() in ('true', '1', 't')
