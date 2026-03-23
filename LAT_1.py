import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import math

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem WebGIS Ukur", page_icon="🌍", layout="wide")

# --- PANGKALAN DATA PENGGUNA ---
users_db = {
    "admin": {"name": "MUHAMMAD UMAR BIN ZULKARNAIN", "password": "12345"},
    "fakhrulis": {"name": "FAKHRULIS", "password": "12345"},
    "Aniqs": {"name": "ANIQS", "password": "12345"}
}

# --- FUNGSI PENGIRAAN ---
def kira_bering_jarak(e1, n1, e2, n2):
    de = e2 - e1
    dn = n2 - n1
    jarak = math.sqrt(de**2 + dn**2)
    bering = math.degrees(math.atan2(de, dn))
    if bering < 0:
        bering += 360
    return jarak, bering

# --- SISTEM LOG MASUK ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h2 style='text-align: center;'>🔒 Log Masuk Sistem WebGIS</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user_id = st.text_input("ID Pengguna")
        password = st.text_input("Kata Laluan", type="password")
        if st.button("Log Masuk", use_container_width=True):
            if user_id in users_db and password == users_db[user_id]['password']:
                st.session_state['logged_in'] = True
                st.session_state['current_user'] = users_db[user_id]['name']
                st.rerun()
            else:
                st.error("ID atau Kata Laluan salah!")
else:
    # --- HALAMAN UTAMA WEB ---
    st.sidebar.title(f"👋 {st.session_state['current_user']}")
    
    st.sidebar.markdown("### 🎛️ Kawalan Visual")
    saiz_marker = st.sidebar.slider("Saiz Marker", 1, 50, 22)
    tahap_zoom = st.sidebar.slider("Tahap Zoom", 10, 24, 19)
    
    if st.sidebar.button("🚪 Log Keluar"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.title("SISTEM SURVEY LOT 🌍")
    st.markdown("*Politeknik Ungku Omar | Jabatan Kejuruteraan Awam*")

    # Muat Naik CSV
    uploaded_file = st.file_uploader("📂 Muat Naik Fail CSV", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if all(col in df.columns for col in ['STN', 'E', 'N']):
                # Kiraan
                poly_geom = Polygon(zip(df['E'], df['N']))
                gdf = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs="EPSG:4390")
                keluasan = gdf.area.iloc[0]
                
                jarak_total = sum([kira_bering_jarak(df.iloc[i]['E'], df.iloc[i]['N'], 
                                                     df.iloc[(i+1)%len(df)]['E'], 
                                                     df.iloc[(i+1)%len(df)]['N'])[0] for i in range(len(df))])
                
                st.success(f"✅ Data Dimuat Naik! | Bilangan Stesen: {len(df)} | Luas: {keluasan:.3f} m² | Perimeter: {jarak_total:.3f} m")
                
                # Pemetaan
                gdf_wgs84 = gdf.to_crs(epsg=4326)
                lat_tengah, lon_tengah = gdf_wgs84.centroid.y.iloc[0], gdf_wgs84.centroid.x.iloc[0]
                
                m = folium.Map(location=[lat_tengah, lon_tengah], zoom_start=tahap_zoom)
                folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Satelit').add_to(m)
                
                folium.GeoJson(gdf_wgs84, style_function=lambda x: {'fillColor': '#A020F0', 'color': 'none', 'fillOpacity': 0.3}).add_to(m)
                
                for i in range(len(df)):
                    e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
                    pt = gpd.GeoSeries([Point(e1, n1)], crs="EPSG:4390").to_crs(epsg=4326)
                    folium.CircleMarker(
                        location=[pt.y.iloc[0], pt.x.iloc[0]], radius=saiz_marker / 4, color='red', fill=True, fill_color='red',
                        tooltip=f"Stesen: {df.iloc[i]['STN']}"
                    ).add_to(m)
                
                st_folium(m, width=900, height=500)
            else:
                st.error("Fail CSV mesti ada kolum 'STN', 'E', dan 'N'.")
        except Exception as e:
            st.error(f"Ralat membaca fail: {e}")
