from enum import Enum


class ItemType(str, Enum):
    EQUIPMENT = "Equipment"
    MATERIAL = "Material"
    CONSUMABLE = "Consumable"
    COLLECTIBLE = "Collectible"
    CONTAINER = "Container"
    UNKNOWN = "Unknown"


class Rarity(str, Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    EPIC = "Epic"
    LEGENDARY = "Legendary"
    ETHEREAL = "Ethereal"
    NORMAL = "Normal"
    FINE = "Fine"
    UNKNOWN = "Unknown"


RARITY_SUFFIXES = {
    "_ethereal": Rarity.ETHEREAL,
    "_legendary": Rarity.LEGENDARY,
    "_epic": Rarity.EPIC,
    "_rare": Rarity.RARE,
    "_uncommon": Rarity.UNCOMMON,
    "_common": Rarity.COMMON,
}

RARITY_ORDER = {
    Rarity.UNKNOWN: 0,
    Rarity.NORMAL: 1,
    Rarity.COMMON: 1,
    Rarity.FINE: 2,
    Rarity.UNCOMMON: 3,
    Rarity.RARE: 4,
    Rarity.EPIC: 5,
    Rarity.LEGENDARY: 6,
    Rarity.ETHEREAL: 7,
}

RARITY_COLORS = {
    Rarity.UNKNOWN: "#888888",
    Rarity.NORMAL: "#aaaaaa",
    Rarity.COMMON: "#aaaaaa",
    Rarity.FINE: "#33cc33",
    Rarity.UNCOMMON: "#1eff00",
    Rarity.RARE: "#0070dd",
    Rarity.EPIC: "#a335ee",
    Rarity.LEGENDARY: "#ff8000",
    Rarity.ETHEREAL: "#00ccff",
}


class EquipmentSlot(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    FEET = "feet"
    TOOLS = "tools"
    RING = "ring"
    NECK = "neck"
    CAPE = "cape"
    BACK = "back"
    HANDS = "hands"
    UNKNOWN = "unknown"
