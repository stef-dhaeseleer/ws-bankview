import json
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from item_registry import ItemRegistry
from user_data import load_user_data
from ui.sidebar import render_sidebar
from ui.dashboard import render_dashboard
from ui.bank_browser import render_bank_browser
from ui.tabs_ui import render_tabs
from ui.filters_ui import render_filters
from ui.crafting_tree import render_crafting_tree

st.set_page_config(
    page_title="WS BankView",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_resource
def get_registry() -> ItemRegistry:
    reg = ItemRegistry()
    reg.load()
    return reg


registry = get_registry()

# ---------------------------------------------------------------------------
# localStorage bootstrap — runs once per browser session to restore persisted
# config and user data after a page refresh.
# ---------------------------------------------------------------------------
if not st.session_state.get("ls_loaded"):
    _ls_raw = streamlit_js_eval(
        js_expressions="""(() => JSON.stringify({
            bankview: localStorage.getItem('BANKVIEW_CONFIG'),
            crafting: localStorage.getItem('CRAFTING_CONFIG'),
            user_data: localStorage.getItem('BANKVIEW_USER_DATA')
        }))()""",
        key="ls_bootstrap",
    )
    if _ls_raw:
        try:
            _ls = json.loads(_ls_raw)
            if _ls.get("bankview"):
                from models import BankViewConfig
                st.session_state["bankview_config"] = BankViewConfig.model_validate(
                    json.loads(_ls["bankview"])
                )
            if _ls.get("crafting"):
                st.session_state["crafting_tree_config"] = json.loads(_ls["crafting"])
            if _ls.get("user_data"):
                st.session_state["user_data_raw"] = _ls["user_data"]
                st.session_state["user_data_paste_text"] = _ls["user_data"]
        except Exception:
            pass
        st.session_state["ls_loaded"] = True
        st.rerun()

# Persist user data to localStorage when flagged by a sidebar action.
# Runs on the rerun triggered by st.rerun() in the sidebar, so no additional
# rerun follows and the streamlit_js_eval component can execute its JS cleanly.
if "_save_user_data_to_ls" in st.session_state:
    _to_save = st.session_state.pop("_save_user_data_to_ls")
    _n = st.session_state.get("_ls_user_data_save_n", 0) + 1
    st.session_state["_ls_user_data_save_n"] = _n
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('BANKVIEW_USER_DATA', {json.dumps(_to_save)})",
        key=f"ls_user_data_save_{_n}",
    )

# Parse user data if available
user = None
if "user_data_raw" in st.session_state:
    user = load_user_data(st.session_state["user_data_raw"])

# Sidebar
render_sidebar(user, registry)

# Main content
if user is None:
    st.title("🏦 WS BankView")
    st.markdown(
        """
        Welcome to **WS BankView** — a WalkScape bank viewer.

        Upload your character export JSON in the sidebar to get started.

        ### Features
        - 📊 **Dashboard** — overview of coins, bank value, equipped gear, and top items
        - 🏦 **Bank Browser** — search, sort, and filter all your items
        - 📑 **Bank Tabs** — create custom tabs and manually assign items
        - 🔍 **Bank Filters** — build dynamic rule-based filters
        - 🌿 **Crafting Tree** — pick a recipe and see the full ingredient tree with owned quantities
        """
    )
else:
    tab_dashboard, tab_browser, tab_tabs, tab_filters, tab_crafting = st.tabs(
        ["📊 Dashboard", "🏦 Bank Browser", "📑 Tabs", "🔍 Filters", "🌿 Crafting Tree"]
    )

    with tab_dashboard:
        render_dashboard(user, registry)

    with tab_browser:
        render_bank_browser(user, registry)

    with tab_tabs:
        render_tabs(user, registry)

    with tab_filters:
        render_filters(user, registry)

    with tab_crafting:
        render_crafting_tree(user, registry)
