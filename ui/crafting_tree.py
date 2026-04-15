from __future__ import annotations
from typing import Dict, List, Optional, Set
import json
import math
import os
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

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


# ---------------------------------------------------------------------------
# Crafting config (per-recipe yield overrides)
# ---------------------------------------------------------------------------

_CRAFTING_CONFIG_PATH = "crafting_tree_config.json"
_SS_KEY = "crafting_tree_config"
_LS_KEY = "CRAFTING_CONFIG"
_EMPTY_CONFIG: dict = {"recipe_yields": {}, "favorites": []}


def _load_raw_config() -> dict:
    """Return the crafting config dict from session state, seeding from disk locally."""
    if _SS_KEY not in st.session_state:
        if not st.session_state.get("ls_loaded") and os.path.exists(_CRAFTING_CONFIG_PATH):
            with open(_CRAFTING_CONFIG_PATH, "r", encoding="utf-8") as f:
                st.session_state[_SS_KEY] = json.load(f)
        else:
            st.session_state[_SS_KEY] = dict(_EMPTY_CONFIG)
    return st.session_state[_SS_KEY]


def _save_raw_config(data: dict) -> None:
    """Write the crafting config dict to session state and persist to localStorage."""
    st.session_state[_SS_KEY] = data
    payload = json.dumps(json.dumps(data, ensure_ascii=False))
    n = st.session_state.get("_ls_crafting_save_n", 0) + 1
    st.session_state["_ls_crafting_save_n"] = n
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('{_LS_KEY}', {payload})",
        key=f"ls_crafting_config_save_{n}",
    )


def load_crafting_config() -> Dict[str, float]:
    """Return {recipe_id: effective_yield} overrides from disk."""
    return {k: float(v) for k, v in _load_raw_config().get("recipe_yields", {}).items()}


def save_crafting_config(yield_config: Dict[str, float]) -> None:
    """Persist per-recipe yield overrides to disk without touching other config keys."""
    data = _load_raw_config()
    data["recipe_yields"] = yield_config
    _save_raw_config(data)


def load_favorites() -> List[str]:
    """Return the ordered list of favourite recipe IDs."""
    return list(_load_raw_config().get("favorites", []))


def save_favorites(favorites: List[str]) -> None:
    """Persist favourite recipe IDs to disk without touching other config keys."""
    data = _load_raw_config()
    data["favorites"] = favorites
    _save_raw_config(data)


def _fine_variant(item_id: str, registry: ItemRegistry) -> Optional[str]:
    """Return the fine variant item_id if it exists in the registry, else None."""
    candidate = item_id.lower() + "_fine"
    info = registry.get_item(candidate)
    # get_item returns an inferred stub for unknown items; check it was actually registered
    from utils.constants import ItemType
    if info.item_type != ItemType.UNKNOWN:
        return candidate
    return None


def _build_tree(
    item_id: str,
    needed: int,
    registry: ItemRegistry,
    user: UserData,
    chosen_recipes: Dict[str, str],   # item_id -> recipe_id
    chosen_alts: Dict[str, int],       # "<recipe_id>:<slot_idx>" -> alt_idx
    visited: Optional[Set[str]] = None,
    depth: int = 0,
    use_fine: bool = False,
    yield_config: Optional[Dict[str, float]] = None,
) -> dict:
    """Recursively build a crafting tree node.

    Returns a dict with:
        item_id, display_name, needed, owned, depth,
        recipe (or None if raw material),
        children (list of tree nodes),
        is_fine (bool – True when this node is a fine-substituted ingredient)
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
        "is_fine": False,
    }

    # Avoid infinite recursion on cyclic recipes
    if item_id.lower() in visited:
        return node

    # Fine items share the same recipe as their base counterpart; strip suffix for lookup
    recipe_lookup_id = item_id[:-5] if item_id.lower().endswith("_fine") else item_id
    recipes = registry.get_recipes_for_item(recipe_lookup_id)
    if not recipes:
        return node

    # Pick which recipe the user selected (default: first)
    # Use the base item key for chosen_recipes (fine variants share the base recipe)
    recipe_key = recipe_lookup_id.lower()
    selected_recipe_id = chosen_recipes.get(recipe_key, recipes[0]["id"])
    recipe = next((r for r in recipes if r["id"] == selected_recipe_id), recipes[0])
    node["recipe"] = recipe

    # materials is a list of slots; each slot is a list of alternatives
    slots: List[List[dict]] = recipe.get("materials", [])
    base_yield = float(recipe.get("output_quantity", 1))
    multiplier = (yield_config or {}).get(recipe["id"], 1.0)
    effective_yield = base_yield * multiplier

    # How many recipe runs do we need?
    runs = math.ceil(needed / effective_yield)

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

        # Fine substitution: replace with fine variant when available
        is_fine = False
        if use_fine:
            fine_id = _fine_variant(child_id, registry)
            if fine_id is not None:
                child_id = fine_id
                is_fine = True

        child_node = _build_tree(
            child_id,
            child_amount,
            registry,
            user,
            chosen_recipes,
            chosen_alts,
            visited | {item_id.lower()},
            depth + 1,
            use_fine=use_fine,
            yield_config=yield_config,
        )
        child_node["is_fine"] = is_fine
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
    yield_config: Dict[str, float],
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

    col_label, col_owned, col_needed, col_status, col_yield = st.columns([4, 1, 1, 2, 2])
    with col_label:
        # Show crafting info when there's a recipe
        recipe = node.get("recipe")
        if recipe:
            out_qty = recipe.get("output_quantity", 1)
            suffix = f"  (craft {out_qty}x)  "
        else:
            suffix = ""
        fine_badge = " ✨" if node.get("is_fine") else ""
        if indent_px > 0:
            st.markdown(
                f'<div style="padding-left:{indent_px}px">{label}{fine_badge}{suffix}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**{label}**{fine_badge}{suffix}")

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

    with col_yield:
        recipe = node.get("recipe")
        if recipe:
            recipe_id = recipe["id"]
            base_yield = float(recipe.get("output_quantity", 1))
            current_multiplier = yield_config.get(recipe_id, 1.0)
            new_multiplier = st.number_input(
                "Yield multiplier",
                min_value=0.01,
                value=current_multiplier,
                step=0.1,
                format="%.2f",
                key=f"yield_{recipe_id}_{depth}",
                label_visibility="collapsed",
                help=f"Multiplier on top of base output ({base_yield}x). E.g. 2.00 → {base_yield * 2:.4g}x outputs per craft.",
            )
            if abs(new_multiplier - current_multiplier) > 1e-9:
                yield_config[recipe_id] = new_multiplier
                save_crafting_config(yield_config)
                rerun_flag.append(True)

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
        recipe_lookup_id = item_id[:-5] if item_id.lower().endswith("_fine") else item_id
        recipe_key = recipe_lookup_id.lower()
        all_recipes = registry.get_recipes_for_item(recipe_lookup_id)
        if len(all_recipes) > 1:
            current_rid = chosen_recipes.get(recipe_key, all_recipes[0]["id"])
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
                chosen_recipes[recipe_key] = recipe_ids[choice_r]
                rerun_flag.append(True)

    # Recurse
    for child in node["children"]:
        _render_node(child, registry, user, chosen_recipes, chosen_alts, rerun_flag, yield_config)


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

    favorites = load_favorites()

    # Default to the top favourite on first load (before the selectbox widget is created)
    if "crafting_tree_recipe" not in st.session_state and favorites:
        first_fav_name = next(
            (r["name"] for r in recipe_options if r["id"] == favorites[0]), None
        )
        if first_fav_name:
            st.session_state["crafting_tree_recipe"] = first_fav_name

    # ---- Favourites panel ----
    fav_header = f"⭐ Favourites ({len(favorites)})" if favorites else "⭐ Favourites"
    with st.expander(fav_header, expanded=False):
        if not favorites:
            st.caption("No favourites yet. Select a recipe below and click **☆ Add to Favourites**.")
        else:
            st.caption("The top recipe is loaded by default when you open this tab.")
            # Resolve favourites to recipe objects (skip IDs that no longer exist)
            fav_rows = [
                (fid, next((r for r in recipe_options if r["id"] == fid), None))
                for fid in favorites
            ]
            fav_rows = [(fid, r) for fid, r in fav_rows if r is not None]

            for i, (fid, r) in enumerate(fav_rows):
                col_pos, col_name, col_load, col_up, col_down, col_remove = st.columns(
                    [1, 5, 1, 1, 1, 1]
                )
                with col_pos:
                    st.markdown("🥇" if i == 0 else f"**{i + 1}.**")
                with col_name:
                    st.write(r["name"])
                with col_load:
                    if st.button("▶", key=f"fav_load_{fid}", help="Load this recipe"):
                        st.session_state["crafting_tree_recipe"] = r["name"]
                        st.rerun()
                with col_up:
                    if i > 0:
                        if st.button("↑", key=f"fav_up_{fid}", help="Move up"):
                            favorites.insert(i - 1, favorites.pop(i))
                            save_favorites(favorites)
                            st.rerun()
                with col_down:
                    if i < len(fav_rows) - 1:
                        if st.button("↓", key=f"fav_down_{fid}", help="Move down"):
                            favorites.insert(i + 1, favorites.pop(i))
                            save_favorites(favorites)
                            st.rerun()
                with col_remove:
                    if st.button("✕", key=f"fav_remove_{fid}", help="Remove from favourites"):
                        favorites.remove(fid)
                        save_favorites(favorites)
                        st.rerun()

    selected_label = st.selectbox(
        "Select a recipe",
        recipe_labels,
        key="crafting_tree_recipe",
    )
    selected_idx = recipe_labels.index(selected_label)
    root_recipe = recipe_options[selected_idx]
    root_item_id = root_recipe["output_item_id"]
    root_item_info = registry.get_item(root_item_id)

    # Favourite toggle for the currently selected recipe
    is_fav = root_recipe["id"] in favorites
    fav_btn_label = "★ Remove from Favourites" if is_fav else "☆ Add to Favourites"
    if st.button(fav_btn_label, key="crafting_fav_toggle"):
        if is_fav:
            favorites.remove(root_recipe["id"])
        else:
            favorites.append(root_recipe["id"])
        save_favorites(favorites)
        st.rerun()

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

    use_fine: bool = st.toggle(
        "✨ Use fine materials",
        value=False,
        key="crafting_use_fine",
        help="Substitute each ingredient with its fine variant when one exists.",
    )

    yield_config = load_crafting_config()

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
        use_fine=use_fine,
        yield_config=yield_config,
    )

    # ---- Render tree ----
    col_label_h, col_owned_h, col_needed_h, col_status_h, col_yield_h = st.columns([4, 1, 1, 2, 2])
    with col_label_h:
        st.markdown("**Item**")
    with col_owned_h:
        st.markdown("**Owned**")
    with col_needed_h:
        st.markdown("**Needed**")
    with col_status_h:
        st.markdown("**Status**")
    with col_yield_h:
        st.markdown("**Crafts/material**")

    rerun_flag: list = []
    _render_node(tree, registry, user, chosen_recipes, chosen_alts, rerun_flag, yield_config)

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
