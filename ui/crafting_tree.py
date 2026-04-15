from __future__ import annotations
from typing import Dict, List, Optional, Set
import streamlit as st

from user_data import UserData
from item_registry import ItemRegistry


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _owned_qty(item_id: str, user: UserData) -> int:
    """Return total owned quantity across all storage."""
    total = 0
    for storage in user.get_all_storage().values():
        total += storage.get(item_id.lower(), 0)
    return total


def _build_tree(
    item_id: str,
    needed: int,
    registry: ItemRegistry,
    user: UserData,
    chosen_recipes: Dict[str, str],   # item_id -> recipe_id
    chosen_alts: Dict[str, int],       # "<recipe_id>:<slot_idx>" -> alt_idx
    visited: Optional[Set[str]] = None,
    depth: int = 0,
) -> dict:
    """Recursively build a crafting tree node.

    Returns a dict with:
        item_id, display_name, needed, owned, depth,
        recipe (or None if raw material),
        children (list of tree nodes),
        alternatives (list of lists of {item_id, amount} for each slot)
    """
    if visited is None:
        visited = set()

    item_info = registry.get_item(item_id)
    owned = _owned_qty(item_id, user)
    node: dict = {
        "item_id": item_id,
        "display_name": item_info.display_name,
        "needed": needed,
        "owned": owned,
        "depth": depth,
        "recipe": None,
        "children": [],
    }

    # Avoid infinite recursion on cyclic recipes
    if item_id.lower() in visited:
        return node

    recipes = registry.get_recipes_for_item(item_id)
    if not recipes:
        return node

    # Pick which recipe the user selected (default: first)
    selected_recipe_id = chosen_recipes.get(item_id.lower(), recipes[0]["id"])
    recipe = next((r for r in recipes if r["id"] == selected_recipe_id), recipes[0])
    node["recipe"] = recipe

    # materials is a list of slots; each slot is a list of alternatives
    slots: List[List[dict]] = recipe.get("materials", [])
    output_qty: int = recipe.get("output_quantity", 1)

    # How many recipe runs do we need?
    import math
    runs = math.ceil(needed / output_qty)

    children = []
    for slot_idx, alt_group in enumerate(slots):
        if not alt_group:
            continue
        slot_key = f"{recipe['id']}:{slot_idx}"
        alt_idx = chosen_alts.get(slot_key, 0)
        alt_idx = min(alt_idx, len(alt_group) - 1)

        chosen_ingredient = alt_group[alt_idx]
        child_id = chosen_ingredient["item_id"]
        child_amount = chosen_ingredient["amount"] * runs

        child_node = _build_tree(
            child_id,
            child_amount,
            registry,
            user,
            chosen_recipes,
            chosen_alts,
            visited | {item_id.lower()},
            depth + 1,
        )
        child_node["alt_group"] = alt_group
        child_node["alt_idx"] = alt_idx
        child_node["slot_idx"] = slot_idx
        child_node["parent_recipe_id"] = recipe["id"]
        children.append(child_node)

    node["children"] = children
    return node


def _collect_totals(node: dict, totals: Dict[str, dict]):
    """Aggregate leaf-level (raw material) needs across the whole tree."""
    if not node["children"]:
        item_id = node["item_id"]
        if item_id not in totals:
            totals[item_id] = {
                "display_name": node["display_name"],
                "needed": 0,
                "owned": node["owned"],
            }
        totals[item_id]["needed"] += node["needed"]
    else:
        for child in node["children"]:
            _collect_totals(child, totals)


# ---------------------------------------------------------------------------
# UI rendering helpers
# ---------------------------------------------------------------------------

DEPTH_INDENT = 28  # px per depth level

_STATUS_COLORS = {
    "ok": "#2e7d32",       # green – have enough
    "partial": "#f57c00",  # orange – have some
    "missing": "#c62828",  # red – have none
}


def _status(owned: int, needed: int) -> str:
    if owned >= needed:
        return "ok"
    if owned > 0:
        return "partial"
    return "missing"


def _status_icon(status: str) -> str:
    return {"ok": "✅", "partial": "⚠️", "missing": "❌"}[status]


def _render_node(
    node: dict,
    registry: ItemRegistry,
    user: UserData,
    chosen_recipes: Dict[str, str],
    chosen_alts: Dict[str, int],
    rerun_flag: list,
):
    """Render a single tree node with indentation, then recurse into children."""
    depth = node["depth"]
    item_id = node["item_id"]
    owned = node["owned"]
    needed = node["needed"]
    status = _status(owned, needed)
    icon = _status_icon(status)

    indent_px = depth * DEPTH_INDENT
    # Use HTML for indentation inside the dataframe-free layout
    prefix = "─" * depth
    label = f"{prefix} {node['display_name']}" if depth > 0 else node["display_name"]

    col_label, col_owned, col_needed, col_status = st.columns([5, 1, 1, 1])
    with col_label:
        # Show crafting info when there's a recipe
        recipe = node.get("recipe")
        if recipe:
            skill = recipe.get("skill", "").title()
            level = recipe.get("level", "?")
            out_qty = recipe.get("output_quantity", 1)
            suffix = f"  _(craft {out_qty}x · {skill} lv.{level})_"
        else:
            suffix = ""
        if indent_px > 0:
            st.markdown(
                f'<div style="padding-left:{indent_px}px">{label}{suffix}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**{label}**{suffix}")

    with col_owned:
        st.write(owned)

    with col_needed:
        st.write(needed)

    with col_status:
        color = _STATUS_COLORS[status]
        st.markdown(
            f'<span style="color:{color};font-weight:bold">{icon}</span>',
            unsafe_allow_html=True,
        )

    # Alternative selector – only when a slot has more than one option
    if node.get("alt_group") and len(node["alt_group"]) > 1:
        alt_group = node["alt_group"]
        slot_key = f"{node['parent_recipe_id']}:{node['slot_idx']}"
        current_alt = node["alt_idx"]
        alt_labels = [
            f"{registry.get_item(a['item_id']).display_name} ×{a['amount']}"
            for a in alt_group
        ]
        choice = st.selectbox(
            "Use alternative ingredient:",
            range(len(alt_labels)),
            index=current_alt,
            format_func=lambda i: alt_labels[i],
            key=f"alt_{slot_key}_{depth}",
            label_visibility="collapsed",
        )
        if choice != current_alt:
            chosen_alts[slot_key] = choice
            rerun_flag.append(True)

    # Recipe selector – only when multiple recipes produce this item
    if node.get("recipe"):
        all_recipes = registry.get_recipes_for_item(item_id)
        if len(all_recipes) > 1:
            current_rid = chosen_recipes.get(item_id.lower(), all_recipes[0]["id"])
            recipe_labels = [r["name"] for r in all_recipes]
            recipe_ids = [r["id"] for r in all_recipes]
            current_ridx = recipe_ids.index(current_rid) if current_rid in recipe_ids else 0
            choice_r = st.selectbox(
                "Recipe variant:",
                range(len(recipe_labels)),
                index=current_ridx,
                format_func=lambda i: recipe_labels[i],
                key=f"recipe_choice_{item_id.lower()}_{depth}",
                label_visibility="collapsed",
            )
            if choice_r != current_ridx:
                chosen_recipes[item_id.lower()] = recipe_ids[choice_r]
                rerun_flag.append(True)

    # Recurse
    for child in node["children"]:
        _render_node(child, registry, user, chosen_recipes, chosen_alts, rerun_flag)


# ---------------------------------------------------------------------------
# Main render entry point
# ---------------------------------------------------------------------------

def render_crafting_tree(user: UserData, registry: ItemRegistry):
    st.header("🌿 Crafting Tree")

    recipes = registry.get_recipes()
    if not recipes:
        st.error("No recipe data found.")
        return

    # ---- Recipe selector ----
    recipe_options = sorted(recipes, key=lambda r: r["name"])
    recipe_labels = [r["name"] for r in recipe_options]
    recipe_ids = [r["id"] for r in recipe_options]

    selected_label = st.selectbox(
        "Select a recipe",
        recipe_labels,
        key="crafting_tree_recipe",
    )
    selected_idx = recipe_labels.index(selected_label)
    root_recipe = recipe_options[selected_idx]
    root_item_id = root_recipe["output_item_id"]
    root_item_info = registry.get_item(root_item_id)

    col_qty, col_info = st.columns([2, 5])
    with col_qty:
        quantity = st.number_input(
            "Quantity to craft",
            min_value=1,
            value=1,
            step=1,
            key="crafting_tree_qty",
        )
    with col_info:
        out_qty = root_recipe.get("output_quantity", 1)
        skill = root_recipe.get("skill", "").title()
        level = root_recipe.get("level", "?")
        service = root_recipe.get("service", "").replace("_", " ").title()
        st.caption(
            f"**Output:** {root_item_info.display_name} ×{out_qty}  \n"
            f"**Skill:** {skill} lv.{level}  |  **Service:** {service}"
        )

    st.divider()

    # ---- Session state for persisting choices ----
    if "crafting_chosen_recipes" not in st.session_state:
        st.session_state.crafting_chosen_recipes = {}
    if "crafting_chosen_alts" not in st.session_state:
        st.session_state.crafting_chosen_alts = {}

    chosen_recipes: Dict[str, str] = st.session_state.crafting_chosen_recipes
    chosen_alts: Dict[str, int] = st.session_state.crafting_chosen_alts

    # Force root recipe for the top-level item
    chosen_recipes[root_item_id.lower()] = root_recipe["id"]

    # ---- Build tree ----
    tree = _build_tree(
        root_item_id,
        quantity,
        registry,
        user,
        chosen_recipes,
        chosen_alts,
    )

    # ---- Render tree ----
    col_label_h, col_owned_h, col_needed_h, col_status_h = st.columns([5, 1, 1, 1])
    with col_label_h:
        st.markdown("**Item**")
    with col_owned_h:
        st.markdown("**Owned**")
    with col_needed_h:
        st.markdown("**Needed**")
    with col_status_h:
        st.markdown("**Status**")

    rerun_flag: list = []
    _render_node(tree, registry, user, chosen_recipes, chosen_alts, rerun_flag)

    if rerun_flag:
        st.rerun()

    # ---- Summary: raw materials totals ----
    st.divider()
    st.subheader("📦 Raw Materials Summary")
    st.caption("Total raw ingredients needed (leaves of the crafting tree).")

    totals: Dict[str, dict] = {}
    _collect_totals(tree, totals)

    if totals:
        import pandas as pd
        rows = []
        for item_id, data in sorted(totals.items(), key=lambda x: x[1]["display_name"].lower()):
            s = _status(data["owned"], data["needed"])
            rows.append({
                "Material": data["display_name"],
                "Owned": data["owned"],
                "Needed": data["needed"],
                "Status": _status_icon(s),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("This recipe has no sub-ingredients (it is a raw craft).")
