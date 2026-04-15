import json
import streamlit as st
from user_data import UserData
from item_registry import ItemRegistry
from utils.constants import RARITY_COLORS


def render_sidebar(user: UserData | None, registry: ItemRegistry):
    with st.sidebar:
        st.title("🏦 WS BankView")
        st.caption("WalkScape Bank Viewer")

        paste_tab, upload_tab = st.tabs(["📋 Paste JSON", "📁 Upload file"])

        with paste_tab:
            pasted = st.text_area(
                "Paste character export JSON",
                height=120,
                placeholder='{"name": "...", "skills": {...}, "bank": {...}, ...}',
                label_visibility="collapsed",
                key="user_data_paste_text",
            )
            btn_col1, btn_col2 = st.columns([1, 1])
            if btn_col1.button("Load", key="btn_load_paste", use_container_width=True):
                try:
                    json.loads(pasted.lstrip("\ufeff"))  # validate JSON
                    st.session_state["user_data_raw"] = pasted
                    st.session_state["_save_user_data_to_ls"] = pasted
                    st.toast("Character data loaded!", icon="✅")
                    st.rerun()
                except (json.JSONDecodeError, ValueError):
                    st.error("Invalid JSON — please paste a valid character export.")
            if user is not None and btn_col2.button("Clear", key="btn_clear_paste", use_container_width=True):
                st.session_state.pop("user_data_raw", None)
                st.session_state["user_data_paste_text"] = ""
                st.rerun()

        with upload_tab:
            uploaded = st.file_uploader(
                "Upload character export",
                type=["json", "txt"],
                help="Upload your WalkScape character export (JSON/TXT)",
                label_visibility="collapsed",
            )
            if uploaded is not None:
                content = uploaded.read().decode("utf-8")
                st.session_state["user_data_raw"] = content
                st.session_state["_save_user_data_to_ls"] = content
                if user is None:
                    st.rerun()

        if user is None:
            st.info("Upload a character export to get started.")
            return

        st.divider()
        st.subheader(f"👤 {user.name}")
        st.caption(f"Version: {user.game_version}")

        col1, col2 = st.columns(2)
        col1.metric("🪙 Coins", f"{user.coins:,}")
        col2.metric("👣 Steps", f"{user.steps:,}")

        value_breakdown = user.calculate_bank_value(registry)
        total_value = sum(value_breakdown.values())
        st.metric("💰 Total Value", f"{total_value:,}")

        st.divider()
        st.subheader("📊 Skills")
        for skill_name, level in sorted(user.skill_levels.items()):
            st.text(f"{skill_name.title():15s} Lv. {level}")

        st.caption(f"Total Level: {user.total_level}")
        st.caption(f"Achievement Points: {user.achievement_points}")

        if user.currencies:
            st.divider()
            st.subheader("🪙 Currencies")
            for currency, amount in sorted(user.currencies.items()):
                if amount > 0:
                    st.text(f"{currency.replace('_', ' ').title():30s} {amount:,}")
