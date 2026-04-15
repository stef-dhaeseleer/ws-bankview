import streamlit as st
from user_data import UserData
from item_registry import ItemRegistry
from utils.constants import RARITY_COLORS


def render_sidebar(user: UserData | None, registry: ItemRegistry):
    with st.sidebar:
        st.title("🏦 WS BankView")
        st.caption("WalkScape Bank Viewer")

        uploaded = st.file_uploader(
            "Upload character export",
            type=["json", "txt"],
            help="Upload your WalkScape character export (JSON/TXT)",
        )

        if uploaded is not None:
            content = uploaded.read().decode("utf-8")
            st.session_state["user_data_raw"] = content

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
