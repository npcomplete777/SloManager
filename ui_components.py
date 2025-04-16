import streamlit as st
import os


def render_logo():
    # Construct the full path for the logo image.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "zurich_logo.png")

    # Attempt to display the image with the use_container_width argument.
    try:
        st.sidebar.image(logo_path, use_container_width=True)
    except TypeError:
        # If use_container_width isn't supported, call image() without it.
        st.sidebar.image(logo_path)
