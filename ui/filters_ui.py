import streamlit as st
from user_data import UserData
from item_registry import ItemRegistry
from models import BankFilter, FilterRule
from config import load_config, save_config, PRESET_FILTERS, get_all_filters
from utils.constants import ItemType, Rarity


FIELD_OPTIONS = {
    "item_type": "Item Type",
    "rarity": "Rarity",
    "name": "Name",
    "item_id": "Item ID",
    "keyword": "Keyword",
    "value": "Unit Value",
    "total_value": "Total Value",
    "source": "Source",
}

OPERATOR_OPTIONS_BY_FIELD = {
    "item_type": ["equals"],
    "rarity": ["equals", "gte"],
    "name": ["contains", "equals"],
    "item_id": ["contains", "equals"],
    "keyword": ["contains", "equals"],
    "value": ["gte", "lte", "equals"],
    "total_value": ["gte", "lte", "equals"],
    "source": ["equals"],
}


def render_filters(user: UserData, registry: ItemRegistry):
    st.header("🔍 Bank Filters")

    config = load_config()
    all_items = user.get_enriched_items(registry)

    # Show preset filters
    st.subheader("📋 Preset Filters")
    for pf in PRESET_FILTERS:
        matched = pf.apply(all_items)
        st.text(f"{pf.name}  →  {len(matched)} items")

    st.divider()

    # Custom filters
    st.subheader("🔧 Custom Filters")

    # Create new filter
    with st.expander("➕ Create New Filter", expanded=False):
        filter_name = st.text_input("Filter name", key="new_filter_name")
        match_mode = st.radio("Match mode", ["ALL", "ANY"], horizontal=True, key="new_filter_match")

        if "new_filter_rules" not in st.session_state:
            st.session_state.new_filter_rules = []

        st.caption("Rules:")
        rules_to_keep = []
        for idx, rule in enumerate(st.session_state.new_filter_rules):
            col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
            with col1:
                st.text(FIELD_OPTIONS.get(rule["field"], rule["field"]))
            with col2:
                st.text(rule["operator"])
            with col3:
                st.text(rule["value"])
            with col4:
                if not st.button("❌", key=f"del_rule_{idx}"):
                    rules_to_keep.append(rule)
        st.session_state.new_filter_rules = rules_to_keep

        # Add rule form
        st.markdown("**Add Rule:**")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            field = st.selectbox("Field", list(FIELD_OPTIONS.keys()),
                                 format_func=lambda x: FIELD_OPTIONS[x],
                                 key="new_rule_field")
        with rc2:
            ops = OPERATOR_OPTIONS_BY_FIELD.get(field, ["equals", "contains"])
            operator = st.selectbox("Operator", ops, key="new_rule_op")
        with rc3:
            # Provide value hints based on field
            if field == "item_type":
                value = st.selectbox("Value", [t.value for t in ItemType], key="new_rule_val_type")
            elif field == "rarity":
                value = st.selectbox("Value", [r.value for r in Rarity], key="new_rule_val_rarity")
            elif field == "source":
                sources = sorted(set(i.source for i in all_items))
                value = st.selectbox("Value", sources, key="new_rule_val_source")
            else:
                value = st.text_input("Value", key="new_rule_val")

        if st.button("Add Rule"):
            st.session_state.new_filter_rules.append({
                "field": field,
                "operator": operator,
                "value": str(value),
            })
            st.rerun()

        # Preview
        if st.session_state.new_filter_rules:
            rules = [FilterRule(**r) for r in st.session_state.new_filter_rules]
            preview_filter = BankFilter(name="Preview", rules=rules, match_mode=match_mode)
            matched = preview_filter.apply(all_items)
            st.caption(f"Preview: {len(matched)} items match")

        if st.button("💾 Save Filter") and filter_name:
            rules = [FilterRule(**r) for r in st.session_state.new_filter_rules]
            new_filter = BankFilter(name=filter_name, rules=rules, match_mode=match_mode)
            config.filters.append(new_filter)
            save_config(config)
            st.session_state.new_filter_rules = []
            st.rerun()

    # List custom filters
    if config.filters:
        for idx, cf in enumerate(config.filters):
            matched = cf.apply(all_items)
            col1, col2 = st.columns([4, 1])
            with col1:
                with st.expander(f"{cf.name}  ({len(matched)} items)"):
                    for rule in cf.rules:
                        st.text(f"  {FIELD_OPTIONS.get(rule.field, rule.field)} {rule.operator} '{rule.value}'")
                    st.caption(f"Match mode: {cf.match_mode}")
            with col2:
                if st.button("🗑️", key=f"del_filter_{idx}"):
                    config.filters.pop(idx)
                    save_config(config)
                    st.rerun()
    else:
        st.caption("No custom filters yet. Create one above!")
