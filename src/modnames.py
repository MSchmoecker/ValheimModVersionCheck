def clean_name(name: str) -> str:
    cleaned = name.strip().replace(" ", "").replace("_", "").replace("-", "")
    if cleaned == "CreatureLevel&LootControl":
        return "CreatureLevelAndLootControl"
    if cleaned == "SpawnThat!":
        return "SpawnThat"
    if cleaned == "DropThat!":
        return "DropThat"
    if cleaned == "PotionsPlus":
        return "PotionPlus"
    if "RainbowTrollArmor" in cleaned:
        return "RainbowTrollArmor"
    if cleaned == "Detalhes.EraSystem":
        return "ValheimEraSystemVAS"
    if "Detalhes." in cleaned:
        return cleaned.replace("Detalhes.", "")
    if cleaned == "kgladder":
        return "BetterLadders"
    if cleaned == "OdinPlusQOL":
        return "OdinsQOL"
    if "ValheimExpanded" in cleaned:
        return "ValheimExpanded"
    if cleaned == "Friendlies":
        return "FriendliesReloaded"
    if cleaned == "FriendliesAssets":
        return "FriendliesReloaded"
    if cleaned == "FriendliesAI":
        return "FriendliesReloaded"
    if cleaned == "SkillInjectorMod":
        return "SkillInjector"
    if cleaned == "SmartContainersMod":
        return "SmartContainers"
    if cleaned == "UsefulTrophiesMod":
        return "UsefulTrophies"
    if cleaned == "BlacksmithTools":
        return "BlacksmithsTools"
    if cleaned == "Basements":
        return "BasementJVLedition"
    if cleaned == "SpeedyPathsMod":
        return "SpeedyPaths"
    if cleaned == "EpicValheimsAdditionsbyHuntard":
        return "EpicValheimsAdditions"
    if cleaned == "AzuMarketplaceSigns":
        return "MarketplaceSigns"
    if cleaned == "DigitalrootMaxDungeonRooms":
        return "DigitalrootValheimMaxDungeonRooms"
    if cleaned == "MorePlayerClothColliders":
        return "MoreandModifiedPlayerClothColliders"
    if cleaned == "CraftyCarts":
        return "CraftyCartsRemake"
    if cleaned == "BronzeStoneworking":
        return "BronzeStonecutting"
    if cleaned == "RagnarsRökareMobAI" or cleaned == "RagnarsRÃ¶kareMobAI":
        return "MobAILib"
    if cleaned == "MossBuild":
        return "BalrondMossBuilds"
    if cleaned == "AFeedBalrondTrough":
        return "BalrondTrough"
    if cleaned == "BalrondBarrell":
        return "BalrondBarrel"
    if cleaned == "BalrondMetalLocker":
        return "BalrondMetalShelf"
    if cleaned == "AllTameableOverhaul":
        return "AllTameableTamingOverhaul"
    if cleaned == "KrumpacZMonsters":
        return "Monsters"
    if cleaned == "MrSerjiConstruction":
        return "Construction"
    if cleaned == "TrashItemsMod":
        return "TrashItems"
    if cleaned == "JotunntheValheimLibrary":
        return "Jotunn"
    return cleaned
