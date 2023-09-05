# Changelog

## 0.4.0
* Switched to Discords Slash Commands
* Added mod list file to every log check
* Removed commands `!checkmods`, `!modlist`
* Renamed commands `!find faulty` to `/find_faulty`, `!thunderstore mods` to `/thunderstore_mods`, `postlog` to `/postlog`

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
