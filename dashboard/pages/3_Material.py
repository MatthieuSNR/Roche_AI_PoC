import streamlit as st

from components import data_access
from components.entity_view import render_entity
from components.filters import entity_selector

st.set_page_config(page_title="Material", layout="wide")
st.title("Material")
snapshots, comments = data_access.require_tables()
material = entity_selector(snapshots, "material", key="selected_material")
st.header(str(material))
render_entity(data_access.get_profile(data_access.version(), "material", material, snapshots, comments),
              "material")
