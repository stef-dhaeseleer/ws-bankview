import json
import math
from typing import Dict, List, Any
from models import EnrichedItem
from item_registry import ItemRegistry


def calculate_level_from_xp(current_xp: int) -> int:
    total = 0
    for i in range(1, 150):
        total += math.floor(i + 300 * (2 ** (i / 7.0)))
        level_xp = math.floor(total / 4)
        if level_xp > current_xp:
            return i
    return 150


def calculate_total_level(skills_data: Dict[str, int]) -> int:
    return sum(calculate_level_from_xp(xp) for xp in skills_data.values())


class UserData:
    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.name: str = raw.get("name", "Unknown")
        self.game_version: str = raw.get("game_version", "")
        self.steps: int = raw.get("steps", 0)
        self.achievement_points: int = raw.get("achievement_points", 0)
        self.coins: int = raw.get("coins", 0)
        self.skills: Dict[str, int] = raw.get("skills", {})
        self.gear: Dict[str, str] = raw.get("gear", {})
        self.bank: Dict[str, int] = self._normalize_storage(raw.get("bank", {}))
        self.inventory: Dict[str, int] = self._normalize_storage(raw.get("inventory", {}))
        self.chests: Dict[str, int] = self._normalize_storage(raw.get("chests", {}))
        self.consumables: Dict[str, int] = self._normalize_storage(raw.get("consumables", {}))
        self.currencies: Dict[str, int] = raw.get("currencies", {})
        self.reputation: Dict[str, float] = {
            k: float(v) for k, v in raw.get("reputation", {}).items()
        }

        # Collectibles: list of strings → dict with qty=1
        raw_collectibles = raw.get("collectibles", [])
        if isinstance(raw_collectibles, list):
            self.collectibles: Dict[str, int] = {c: 1 for c in raw_collectibles}
        else:
            self.collectibles = self._normalize_storage(raw_collectibles)

        # Pets
        self.active_pet = raw.get("pets", {}).get("pet")
        self.available_pets = raw.get("available_pets", [])

    @staticmethod
    def _normalize_storage(data: Any) -> Dict[str, int]:
        if not isinstance(data, dict):
            return {}
        return {str(k): int(v) for k, v in data.items()}

    @property
    def skill_levels(self) -> Dict[str, int]:
        return {name: calculate_level_from_xp(xp) for name, xp in self.skills.items()}

    @property
    def total_level(self) -> int:
        return sum(self.skill_levels.values())

    def get_all_storage(self) -> Dict[str, Dict[str, int]]:
        return {
            "bank": self.bank,
            "inventory": self.inventory,
            "chests": self.chests,
            "consumables": self.consumables,
            "collectibles": self.collectibles,
        }

    def get_equipped_items(self) -> Dict[str, str]:
        return {slot: item_id for slot, item_id in self.gear.items() if item_id}

    def get_enriched_items(self, registry: ItemRegistry) -> List[EnrichedItem]:
        items = []
        for source_name, storage in self.get_all_storage().items():
            for item_id, qty in storage.items():
                if qty <= 0:
                    continue
                info = registry.get_item(item_id)
                items.append(EnrichedItem(
                    item_id=item_id,
                    quantity=qty,
                    info=info,
                    source=source_name,
                ))
        # Equipped gear
        for slot, item_id in self.get_equipped_items().items():
            info = registry.get_item(item_id)
            items.append(EnrichedItem(
                item_id=item_id,
                quantity=1,
                info=info,
                source="gear",
            ))
        return items

    def calculate_bank_value(self, registry: ItemRegistry) -> Dict[str, int]:
        breakdown = {}
        for section_name, storage in self.get_all_storage().items():
            total = 0
            for item_id, qty in storage.items():
                if qty > 0:
                    total += registry.get_value(item_id) * qty
            breakdown[section_name] = total
        # Gear value
        gear_val = 0
        for slot, item_id in self.get_equipped_items().items():
            gear_val += registry.get_value(item_id)
        breakdown["gear"] = gear_val
        return breakdown


def load_user_data(file_content: str) -> UserData:
    # Strip UTF-8 BOM if present
    content = file_content.lstrip("\ufeff")
    data = json.loads(content)
    return UserData(data)
