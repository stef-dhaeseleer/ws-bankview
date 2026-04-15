import json
import os
from models import BankViewConfig, BankTab, BankFilter, FilterRule
from utils.constants import ItemType, Rarity

CONFIG_PATH = "bankview_config.json"

PRESET_FILTERS = [
    BankFilter(
        name="⭐ Fine Materials",
        rules=[FilterRule(field="item_id", operator="contains", value="_fine")],
        match_mode="ALL",
    ),
    BankFilter(
        name="🛡️ Equipment",
        rules=[FilterRule(field="item_type", operator="equals", value=ItemType.EQUIPMENT.value)],
        match_mode="ALL",
    ),
    BankFilter(
        name="🪨 Materials",
        rules=[FilterRule(field="item_type", operator="equals", value=ItemType.MATERIAL.value)],
        match_mode="ALL",
    ),
    BankFilter(
        name="🧪 Consumables",
        rules=[FilterRule(field="item_type", operator="equals", value=ItemType.CONSUMABLE.value)],
        match_mode="ALL",
    ),
    BankFilter(
        name="📦 Containers",
        rules=[FilterRule(field="item_type", operator="equals", value=ItemType.CONTAINER.value)],
        match_mode="ALL",
    ),
    BankFilter(
        name="🏆 Collectibles",
        rules=[FilterRule(field="item_type", operator="equals", value=ItemType.COLLECTIBLE.value)],
        match_mode="ALL",
    ),
    BankFilter(
        name="💎 Rare+",
        rules=[FilterRule(field="rarity", operator="gte", value=Rarity.RARE.value)],
        match_mode="ALL",
    ),
    BankFilter(
        name="💰 High Value (100+)",
        rules=[FilterRule(field="value", operator="gte", value="100")],
        match_mode="ALL",
    ),
]


def load_config() -> BankViewConfig:
    if not os.path.exists(CONFIG_PATH):
        return BankViewConfig()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return BankViewConfig.model_validate(data)


def save_config(config: BankViewConfig):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)


def get_all_filters(config: BankViewConfig) -> list[BankFilter]:
    return PRESET_FILTERS + config.filters
