import streamlit as st
from item_registry import ItemRegistry
from user_data import load_user_data
from ui.sidebar import render_sidebar
from ui.dashboard import render_dashboard
from ui.bank_browser import render_bank_browser
from ui.tabs_ui import render_tabs
from ui.filters_ui import render_filters

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
        """
    )
else:
    tab_dashboard, tab_browser, tab_tabs, tab_filters = st.tabs(
        ["📊 Dashboard", "🏦 Bank Browser", "📑 Tabs", "🔍 Filters"]
    )

    with tab_dashboard:
        render_dashboard(user, registry)

    with tab_browser:
        render_bank_browser(user, registry)

    with tab_tabs:
        render_tabs(user, registry)

    with tab_filters:
        render_filters(user, registry)
