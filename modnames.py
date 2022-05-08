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
    if "Balrond" in cleaned:
        return cleaned.replace("Balrond", "")
    if "RainbowTrollArmor" in cleaned:
        return "RainbowTrollArmor"
    if cleaned == "kgladder":
        return "BetterLadders"
    if cleaned == "OdinPlusQOL":
        return "OdinsQOL"
    if "ValheimExpanded" in cleaned:
        return "ValheimExpanded"
    if "Friendlies" in cleaned:
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
    return cleaned
