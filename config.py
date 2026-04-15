import json
import os
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from models import BankViewConfig, BankTab, BankFilter, FilterRule
from utils.constants import ItemType, Rarity

CONFIG_PATH = "bankview_config.json"
_SS_KEY = "bankview_config"
_LS_KEY = "BANKVIEW_CONFIG"

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
    if _SS_KEY not in st.session_state:
        # Local dev: seed from disk only before localStorage has been read
        if not st.session_state.get("ls_loaded") and os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.session_state[_SS_KEY] = BankViewConfig.model_validate(data)
        else:
            st.session_state[_SS_KEY] = BankViewConfig()
    return st.session_state[_SS_KEY]


def save_config(config: BankViewConfig):
    st.session_state[_SS_KEY] = config
    payload = json.dumps(json.dumps(config.model_dump(), ensure_ascii=False))
    n = st.session_state.get("_ls_config_save_n", 0) + 1
    st.session_state["_ls_config_save_n"] = n
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('{_LS_KEY}', {payload})",
        key=f"ls_bankview_config_save_{n}",
    )


def get_all_filters(config: BankViewConfig) -> list[BankFilter]:
    return PRESET_FILTERS + config.filters
