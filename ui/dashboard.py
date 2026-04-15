import streamlit as st
from user_data import UserData
from item_registry import ItemRegistry


def render_dashboard(user: UserData, registry: ItemRegistry):
    st.header("📊 Dashboard")

    value_breakdown = user.calculate_bank_value(registry)
    total_value = sum(value_breakdown.values())
    all_items = user.get_enriched_items(registry)
    unique_count = len(set(i.item_id for i in all_items))
    total_count = sum(i.quantity for i in all_items)

    # Hero metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🪙 Coins", f"{user.coins:,}")
    c2.metric("💰 Bank Value", f"{total_value:,}")
    c3.metric("📦 Unique Items", f"{unique_count:,}")
    c4.metric("📊 Total Items", f"{total_count:,}")

    st.divider()

    # Value breakdown
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("💎 Value Breakdown")
        for section, val in sorted(value_breakdown.items(), key=lambda x: -x[1]):
            if val > 0:
                pct = (val / total_value * 100) if total_value > 0 else 0
                st.text(f"{section.title():15s} {val:>10,}  ({pct:.1f}%)")

    with col_right:
        st.subheader("🛡️ Equipped Gear")
        equipped = user.get_equipped_items()
        if equipped:
            for slot, item_id in equipped.items():
                info = registry.get_item(item_id)
                st.text(f"{slot.replace('_', ' ').title():12s} {info.display_name}")
        else:
            st.caption("No gear equipped")

    st.divider()

    # Top 10 most valuable stacks
    st.subheader("🏆 Top 10 Most Valuable Stacks")
    sorted_items = sorted(all_items, key=lambda i: i.total_value, reverse=True)
    top_10 = sorted_items[:10]
    if top_10:
        header_cols = st.columns([3, 1, 1, 1, 1])
        header_cols[0].markdown("**Item**")
        header_cols[1].markdown("**Qty**")
        header_cols[2].markdown("**Unit Value**")
        header_cols[3].markdown("**Total Value**")
        header_cols[4].markdown("**Source**")
        for item in top_10:
            cols = st.columns([3, 1, 1, 1, 1])
            cols[0].text(item.display_name)
            cols[1].text(f"{item.quantity:,}")
            cols[2].text(f"{item.info.value:,}")
            cols[3].text(f"{item.total_value:,}")
            cols[4].text(item.source.title())

    st.divider()

    # Reputation
    if user.reputation:
        st.subheader("🏛️ Reputation")
        for faction, rep in sorted(user.reputation.items(), key=lambda x: -x[1]):
            st.text(f"{faction.replace('_', ' ').title():30s} {rep:,.2f}")

    # Pets
    if user.active_pet or user.available_pets:
        st.divider()
        st.subheader("🐾 Pets")
        if user.active_pet:
            pet = user.active_pet
            st.text(f"Active: {pet.get('name', 'Unknown')} ({pet.get('species', '').replace('_', ' ').title()}) Lv.{pet.get('level', '?')}")
        for pet in user.available_pets:
            st.text(f"  {pet.get('name', 'Unknown')} ({pet.get('species', '').replace('_', ' ').title()}) Lv.{pet.get('level', '?')}")
