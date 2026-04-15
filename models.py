from __future__ import annotations
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from utils.constants import ItemType, Rarity, RARITY_SUFFIXES, RARITY_ORDER


class ItemInfo(BaseModel):
    id: str
    name: str
    display_name: str
    value: int = 0
    item_type: ItemType = ItemType.UNKNOWN
    rarity: Rarity = Rarity.UNKNOWN
    keywords: tuple[str, ...] = Field(default_factory=tuple)
    slot: Optional[str] = None

    @property
    def rarity_rank(self) -> int:
        return RARITY_ORDER.get(self.rarity, 0)


class EnrichedItem(BaseModel):
    item_id: str
    quantity: int
    info: ItemInfo
    source: str = "bank"  # bank, inventory, chests, gear, collectibles

    @property
    def total_value(self) -> int:
        return self.info.value * self.quantity

    @property
    def display_name(self) -> str:
        return self.info.display_name

    @property
    def rarity(self) -> Rarity:
        return self.info.rarity

    @property
    def item_type(self) -> ItemType:
        return self.info.item_type


class FilterRule(BaseModel):
    field: str  # "item_type", "rarity", "keyword", "name"
    operator: str  # "equals", "contains", "in", "gte", "lte"
    value: str

    def matches(self, item: EnrichedItem) -> bool:
        if self.field == "item_type":
            return self._match_value(item.info.item_type.value)
        elif self.field == "rarity":
            if self.operator == "gte":
                target_rank = RARITY_ORDER.get(Rarity(self.value), 0)
                return item.info.rarity_rank >= target_rank
            return self._match_value(item.info.rarity.value)
        elif self.field == "name":
            return self._match_value(item.info.display_name)
        elif self.field == "item_id":
            return self._match_value(item.item_id)
        elif self.field == "keyword":
            for kw in item.info.keywords:
                if self._match_value(kw):
                    return True
            return False
        elif self.field == "value":
            try:
                threshold = int(self.value)
            except ValueError:
                return False
            if self.operator == "gte":
                return item.info.value >= threshold
            elif self.operator == "lte":
                return item.info.value <= threshold
            return item.info.value == threshold
        elif self.field == "total_value":
            try:
                threshold = int(self.value)
            except ValueError:
                return False
            if self.operator == "gte":
                return item.total_value >= threshold
            elif self.operator == "lte":
                return item.total_value <= threshold
            return item.total_value == threshold
        elif self.field == "source":
            return self._match_value(item.source)
        return False

    def _match_value(self, actual: str) -> bool:
        if self.operator == "equals":
            return actual.lower() == self.value.lower()
        elif self.operator == "contains":
            return self.value.lower() in actual.lower()
        elif self.operator == "in":
            targets = [v.strip().lower() for v in self.value.split(",")]
            return actual.lower() in targets
        return False


class BankFilter(BaseModel):
    name: str
    rules: List[FilterRule] = Field(default_factory=list)
    match_mode: str = "ALL"  # ALL or ANY

    def apply(self, items: list[EnrichedItem]) -> list[EnrichedItem]:
        if not self.rules:
            return items
        result = []
        for item in items:
            if self.match_mode == "ALL":
                if all(rule.matches(item) for rule in self.rules):
                    result.append(item)
            else:
                if any(rule.matches(item) for rule in self.rules):
                    result.append(item)
        return result


class BankTab(BaseModel):
    name: str
    icon: str = "📦"
    item_ids: List[str] = Field(default_factory=list)


class BankViewConfig(BaseModel):
    tabs: List[BankTab] = Field(default_factory=list)
    filters: List[BankFilter] = Field(default_factory=list)
