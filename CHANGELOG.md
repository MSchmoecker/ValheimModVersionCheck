# Changelog

## 0.7.0
* Added support for Lethal Company
* Simplified the config file
* Updated  ilspycmd to 8.2.0.7535
* Fixed community format for Thunderstore API calls, allowing more games to be supported

## 0.6.1
* Fixed an error if the first log line isn't formatted correctly
* Fixed errors when the Thunderstore package request fails

## 0.6.0
* Added support for other games, can be configured using the config.yml file inside the config folder
* Added application information for HTTP requests to the Thunderstore API
* Updated  ilspycmd to 8.1.1.7464, this should fix some decompilation issues

## 0.5.3
* Fixed icons from Thunderstore reuploads were preferred over older icons, which are more likely to be the original icons

## 0.5.2
* Added icon_url to API
* Fixed parsing of port environment variable if not set

## 0.5.1
* Added API_ROOT_PATH to environment variables

## 0.5.0
* Added HTTP API

## 0.4.1
* Fixed commands to be synced with all Guilds

## 0.4.0
* Switched to Discords Slash Commands
* Added mod list file to every log check
* Removed commands `!checkmods`, `!modlist`
* Renamed commands `!find faulty` to `/find_faulty`, `!thunderstore mods` to `/thunderstore_mods`, `!postlog` to `/postlog`

## 0.3.1
* Fixed bot trying to create a thread in a thread

## 0.3.0
* Changed the bot to create own threads for version check responses
* Fixed the Nexus API not being called if no API key is provided
* Updated discord.py dependency to 2.3.0

## 0.2.1
* Fixed parsed mod list was shared between different log files

## 0.2.0
* Added Valheim and BepInEx version parsing from log and printing to the message

## 0.1.3
* Removed old ValheimPlus version parse workaround

## 0.1.2
* Fixed ZRpc::HandlePackage errors were not fully written into the error.txt

## 0.1.1
* Fixed Fatal errors were not written into the error.txt
* Fixed the BepInEx pack was not decompiled

## 0.1.0
* Introduced versioning system and changelog
