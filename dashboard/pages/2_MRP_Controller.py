import streamlit as st

from components import data_access
from components.entity_view import render_entity
from components.filters import entity_selector

st.set_page_config(page_title="MRP controller", layout="wide")
st.title("MRP controller")
snapshots, comments = data_access.require_tables()
mrp = entity_selector(snapshots, "mrp_controller")
st.header(str(mrp))
render_entity(data_access.get_profile(data_access.version(), "mrp_controller", mrp, snapshots, comments),
              "mrp_controller", open_material_page="pages/3_Material.py")
