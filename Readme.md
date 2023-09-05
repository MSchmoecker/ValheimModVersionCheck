# Valheim Mod Version Check

## About
A ~~simple~~ over-engineered discord bot that reads mod versions from a logfile and checks those against the Thunderstore API and the Nexus API.

## Quick Usage
Invite this bot to your server using this [link](https://discord.com/api/oauth2/authorize?client_id=972794598856474664&permissions=34359773184&scope=bot).

Uploaded BepInEx log files are automatically parsed and responded.

![example](Docs/DiscordExample.png)

Additional commands are available:
- `/thunderstore_mods [search]`: sends a list of all parsed mods, used by the bot to check log file
- `/postlog`: sends instructions where to find the log file
- `/find_faulty`: sends instructions on how to find a broken mod

## Deploy Your Own Bot
If you want to host your own bot, the easiest way is to use docker-compose.

```yaml
version: "3.3"
services:
  app:
    image: maxschmoecker/valheim-mod-version-check:latest
    environment:
      - PYTHONUNBUFFERED=1
      - DISCORD_TOKEN={your-bot-token}
      - NEXUS_API_KEY={your-nexus-api-key}
      - DECOMPILE_THUNDERSTORE_MODS=false
    volumes:
      - ./data:/app/data/
```

### Decompiling Thunderstore Mods
If the `DECOMPILE_THUNDERSTORE_MODS` environment variable is set to false, only the Thunderstore API will be used.
If the variable is set to true, the bot will automatically download, decompile and extract BepInEx metadata like BepInEx name and version.
This greatly improves the mod detection as mod names and versions often don't match exactly (even after removing spaces, underscores, etc).
Only the latest version of each mod is downloaded and the result is cached but the initial phase can take some time as each available mod has to be downloaded first.
The bot will check every hour to see if new mods should be downloaded.

This means that mod downloads are handled in advance and are independent of log requests.

## Development
- Copy `.env.sample` to `.env` and set necessary values.
- Run `docker-compose up --build` or `python app.py`


## Privacy Policy and Terms of Service
See [Privacy Policy](Docs/PrivacyPolicy.md) and [Terms of Service](Docs/TOS.md)


## Changelog
See [Changelog](CHANGELOG.md)
