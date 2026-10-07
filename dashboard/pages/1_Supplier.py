import streamlit as st

from components import data_access
from components.entity_view import render_entity
from components.filters import entity_selector

st.set_page_config(page_title="Supplier", layout="wide")
st.title("Supplier")
snapshots, comments = data_access.require_tables()
vendor = entity_selector(snapshots, "vendor")
st.header(str(vendor))
render_entity(data_access.get_profile(data_access.version(), "vendor", vendor, snapshots, comments),
              "vendor", open_material_page="pages/3_Material.py")
