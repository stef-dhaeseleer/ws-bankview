import streamlit as st
import pandas as pd
from user_data import UserData
from item_registry import ItemRegistry
from models import EnrichedItem
from utils.constants import ItemType, Rarity, RARITY_COLORS, RARITY_ORDER
from config import get_all_filters, load_config


def render_bank_browser(user: UserData, registry: ItemRegistry):
    st.header("🏦 Bank Browser")

    all_items = user.get_enriched_items(registry)

    # Controls row
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        search = st.text_input("🔍 Search", placeholder="Search by item name...")

    with col2:
        sources = ["All"] + sorted(set(i.source for i in all_items))
        selected_source = st.selectbox("Source", sources)

    with col3:
        type_options = ["All"] + [t.value for t in ItemType]
        selected_type = st.selectbox("Type", type_options)

    with col4:
        sort_options = {
            "Name": lambda i: i.display_name.lower(),
            "Quantity (desc)": lambda i: -i.quantity,
            "Unit Value (desc)": lambda i: -i.info.value,
            "Total Value (desc)": lambda i: -i.total_value,
            "Rarity (desc)": lambda i: -i.info.rarity_rank,
        }
        sort_key = st.selectbox("Sort by", list(sort_options.keys()))

    # Quick filter buttons
    config = load_config()
    all_filters = get_all_filters(config)
    filter_names = ["None"] + [f.name for f in all_filters]
    selected_filter = st.selectbox("Quick Filter", filter_names)

    # Apply filters
    filtered = all_items

    if search:
        search_lower = search.lower()
        filtered = [i for i in filtered if search_lower in i.display_name.lower() or search_lower in i.item_id.lower()]

    if selected_source != "All":
        filtered = [i for i in filtered if i.source == selected_source]

    if selected_type != "All":
        filtered = [i for i in filtered if i.info.item_type.value == selected_type]

    if selected_filter != "None":
        chosen = next((f for f in all_filters if f.name == selected_filter), None)
        if chosen:
            filtered = chosen.apply(filtered)

    # Sort
    filtered.sort(key=sort_options[sort_key])

    # Stats bar
    st.caption(f"Showing {len(filtered)} items  |  Total value: {sum(i.total_value for i in filtered):,}")

    # Render table
    if not filtered:
        st.info("No items match your criteria.")
        return

    _render_item_table(filtered)


def _render_item_table(items: list[EnrichedItem]):
    rows = []
    for item in items:
        rows.append({
            "Item": item.display_name,
            "Qty": item.quantity,
            "Unit Value": item.info.value,
            "Total Value": item.total_value,
            "Type": item.info.item_type.value,
            "Rarity": item.info.rarity.value,
            "Source": item.source.title(),
            "ID": item.item_id,
        })

    df = pd.DataFrame(rows)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Qty": st.column_config.NumberColumn(format="%d"),
            "Unit Value": st.column_config.NumberColumn(format="%d"),
            "Total Value": st.column_config.NumberColumn(format="%d"),
        },
    )
