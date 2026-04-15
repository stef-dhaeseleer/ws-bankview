import streamlit as st
from user_data import UserData
from item_registry import ItemRegistry
from models import BankTab
from config import load_config, save_config


def render_tabs(user: UserData, registry: ItemRegistry):
    st.header("📑 Bank Tabs")

    config = load_config()
    all_items = user.get_enriched_items(registry)
    all_item_ids = sorted(set(i.item_id for i in all_items))

    # Create new tab
    with st.expander("➕ Create New Tab", expanded=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_name = st.text_input("Tab name", key="new_tab_name")
        with col2:
            new_icon = st.text_input("Icon", value="📦", key="new_tab_icon")
        if st.button("Create Tab") and new_name:
            config.tabs.append(BankTab(name=new_name, icon=new_icon))
            save_config(config)
            st.rerun()

    if not config.tabs:
        st.info("No tabs created yet. Create one above!")
        return

    # Tab selector
    tab_names = [f"{t.icon} {t.name}" for t in config.tabs]
    selected_idx = st.selectbox(
        "Select tab",
        range(len(tab_names)),
        format_func=lambda i: tab_names[i],
    )
    tab = config.tabs[selected_idx]

    # Tab actions
    col_act1, col_act2 = st.columns([1, 1])
    with col_act1:
        if st.button("🗑️ Delete Tab", type="secondary"):
            config.tabs.pop(selected_idx)
            save_config(config)
            st.rerun()

    # Items in this tab
    tab_items = [i for i in all_items if i.item_id in tab.item_ids]
    st.caption(f"{len(tab_items)} items in this tab")

    if tab_items:
        import pandas as pd
        rows = []
        for item in sorted(tab_items, key=lambda i: i.display_name.lower()):
            rows.append({
                "Item": item.display_name,
                "Qty": item.quantity,
                "Value": item.info.value,
                "Total": item.total_value,
                "Type": item.info.item_type.value,
                "Rarity": item.info.rarity.value,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()

    # Add items to tab
    st.subheader("Add / Remove Items")
    available_for_add = [i for i in all_item_ids if i not in tab.item_ids]

    with st.form(key=f"add_items_{selected_idx}"):
        selected_to_add = st.multiselect(
            "Add items",
            available_for_add,
            format_func=lambda x: f"{registry.get_item(x).display_name} ({x})",
        )
        if st.form_submit_button("Add Selected"):
            tab.item_ids.extend(selected_to_add)
            save_config(config)
            st.rerun()

    if tab.item_ids:
        with st.form(key=f"remove_items_{selected_idx}"):
            selected_to_remove = st.multiselect(
                "Remove items",
                tab.item_ids,
                format_func=lambda x: f"{registry.get_item(x).display_name} ({x})",
            )
            if st.form_submit_button("Remove Selected"):
                tab.item_ids = [i for i in tab.item_ids if i not in selected_to_remove]
                save_config(config)
                st.rerun()
