# ui_components.py

import streamlit as st
import os

def render_logo():
    """
    Renders the Zurich logo in the sidebar.
    """
    logo_path = os.path.join(os.path.dirname(__file__), "zurich_logo.png")
    st.sidebar.image(logo_path, use_container_width=True)
