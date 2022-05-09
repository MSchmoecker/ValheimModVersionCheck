# Valheim Mod Version Check

## About
A simple discord bot that reads mod versions from a logfile and checks those against the Thunderstore API and the Nexus API.

## Usage
Invite this bot to your server using this [link](https://discord.com/api/oauth2/authorize?client_id=972794598856474664&permissions=100352&scope=bot).\
The discord command `!checkmods` is added. Reply to a message that contains a logfile with the command.

![example](Docs/DiscordExample.png)

## Development
- Copy `.env.sample` to `.env` and set necessary values.
- Run `docker-compose up --build` or `python app.py`
