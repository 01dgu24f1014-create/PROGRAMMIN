import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point, LineString
import folium
from streamlit_folium import st_folium
import math

# Konfigurasi Halaman (Mesti diletak paling atas)
st.set_page_config(page_title="Sistem WebGIS Ukur", layout="wide", page_icon="🗺️")

# ==========================================
# --- SISTEM LOG MASUK (LOGIN PENGGUNA) ---
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 Log Masuk Sistem WebGIS")
    st.write("Sila masukkan ID dan Kata Laluan untuk mencari lot dan mengakses paparan.")
    
    with st.form("login_form"):
        user_id = st.text_input("ID Pengguna")
        password = st.text_input("Kata Laluan", type="password")
        submit_button = st.form_submit_button("Log Masuk")
        
        if submit_button:
            # TUKAR ID DAN PASSWORD DI SINI:
            if user_id == "admin" and password == "12345":
                st.session_state['logged_in'] = True
                st.rerun() # Refresh semula muka surat
            else:
                st.error("Ralat: ID Pengguna atau Kata Laluan tidak sah. Cuba lagi.")
    
    # Berhenti di sini jika belum login. Kod bawah tidak akan dibaca.
    st.stop()

# Tambah butang Log Keluar di menu tepi
if st.sidebar.button("🚪 Log Keluar"):
    st.session_state['logged_in'] = False
    st.rerun()


# ==========================================
# --- KOD ASAL WEBGIS BERMULA DI SINI ---
# ==========================================

st.title("🗺️ Sistem WebGIS Poligon Data Ukur")
st.write("Sistem lengkap untuk visualisasi poligon, pengiraan keluasan, dan eksport data spatial.")

# --- FUNGSI PENGIRAAN BERING & JARAK ---
def kira_bering_jarak(e1, n1, e2, n2):
    de = e2 - e1
    dn = n2 - n1
    jarak = math.sqrt(de**2 + dn**2)
    bering = math.degrees(math.atan2(de, dn))
    if bering < 0:
        bering += 360
    return jarak, bering

def format_bering(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = (deg - d - m/60) * 3600
    return f"{d}° {m}' {s:.0f}\""

# 1. Bahagian Muat Naik Fail & Tetapan
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Muat Naik & Tetapan")
    uploaded_file = st.file_uploader("Pilih fail CSV (Kolum: STN, E, N)", type=["csv"])
    
    # --- KEMAS KINI: Tukar value default kepada 4390 (Johor Grid) ---
    epsg_code = st.text_input("Kod EPSG Sistem Koordinat Anda", value="4390", 
                              help="Lalai: 4390 untuk Kertau / Johor Grid. Ubah mengikut keperluan.")

with col2:
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            if 'E' in df.columns and 'N' in df.columns and 'STN' in df.columns:
                # Kira Bering dan Jarak untuk jadual
                jarak_list = []
                bering_list = []
                for i in range(len(df)):
                    e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
                    e2, n2 = df.iloc[(i+1) % len(df)]['E'], df.iloc[(i+1) % len(df)]['N']
                    j, b = kira_bering_jarak(e1, n1, e2, n2)
                    jarak_list.append(round(j, 3))
                    bering_list.append(format_bering(b))
                
                df_display = df.copy()
                df_display['Jarak (m)'] = jarak_list
                df_display['Bering'] = bering_list
                
                st.subheader("Data Ukur Semasa")
                st.dataframe(df_display, use_container_width=True)
                
            else:
                st.error("Ralat: Fail CSV mesti mempunyai kolum 'STN', 'E', dan 'N'.")
                st.stop()
                
        except Exception as e:
            st.error(f"Ralat membaca fail: {e}")
            st.stop()

st.divider()

if uploaded_file is not None and 'df' in locals():
    # --- PROSES GEOPANDAS (TASK 1 & 2) ---
    poly_geom = Polygon(zip(df['E'], df['N']))
    
    # Kod ini akan auto-convert titik anda menggunakan nilai EPSG (4390)
    gdf = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_code}")
    keluasan = gdf.area.iloc[0]
    
    col_tools, col_map = st.columns([1, 3])
    
    with col_tools:
        st.subheader("2. Kawalan & Analisis")
        
        # TASK 1: Button Kira Luas
        if st.button("📏 Kira Keluasan Auto", type="primary", use_container_width=True):
            st.success(f"**Luas Poligon:** {keluasan:.3f} meter persegi")
        
        st.markdown("---")
        st.write("**Togol Visualisasi (Task 4):**")
        # TASK 4: Switch On/Off Layer
        show_sat = st.checkbox("🌍 Paparkan Imej Satelit", value=True)
        show_stn = st.checkbox("🏷️ Paparkan Label Stesen", value=True)
        show_bearing = st.checkbox("📐 Paparkan Bering & Jarak", value=True)
        
        st.markdown("---")
        # TASK 2: Export Data to GIS
        st.write("**Eksport Data (Task 2):**")
        
        # --- BINA SENARAI KESEMUA CIRI (FEATURES) ---
        features_list = []
        
        # 1. Masukkan Poligon Utama
        features_list.append({
            "geometry": poly_geom, 
            "Kategori": "Lot/Poligon", 
            "Label": "Poligon Utama", 
            "Jarak": "", 
            "Bering": ""
        })
        
        # 2. Masukkan Point (Stesen), Garisan (Sempadan) & Titik Tengah (Bering/Jarak)
        for i in range(len(df)):
            e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
            e2, n2 = df.iloc[(i+1) % len(df)]['E'], df.iloc[(i+1) % len(df)]['N']
            stn_name = str(df.iloc[i]['STN'])
            j, b = kira_bering_jarak(e1, n1, e2, n2)
            
            # Point: Stesen Ukur
            features_list.append({
                "geometry": Point(e1, n1),
                "Kategori": "Stesen",
                "Label": f"STN {stn_name}",
                "Jarak": "",
                "Bering": ""
            })
            
            # Garisan: Sempadan antara dua stesen
            features_list.append({
                "geometry": LineString([(e1, n1), (e2, n2)]),
                "Kategori": "Sempadan",
                "Label": f"Sempadan {stn_name}",
                "Jarak": f"{j:.3f}m",
                "Bering": format_bering(b)
            })
            
            # Point: Titik Tengah untuk mudahkan paparan label Bering/Jarak di GIS
            mid_e, mid_n = (e1 + e2)/2, (n1 + n2)/2
            features_list.append({
                "geometry": Point(mid_e, mid_n),
                "Kategori": "Label Ukur",
                "Label": f"{j:.3f}m | {format_bering(b)}",
                "Jarak": f"{j:.3f}m",
                "Bering": format_bering(b)
            })

        # Tukar senarai tadi kepada GeoDataFrame
        gdf_all_features = gpd.GeoDataFrame(features_list, crs=f"EPSG:{epsg_code}")
        
        # Convert kepada format WGS 84 (EPSG 4326) untuk standard GIS Antarabangsa
        gdf_export = gdf_all_features.to_crs(epsg=4326)
        
        # Convert kepada GeoJSON
        geojson_data = gdf_export.to_json()
        
        # Butang Muat Turun
        st.download_button(
            label="💾 Export to GIS (GeoJSON)", 
            data=geojson_data, 
            file_name="data_gis_lengkap.geojson", 
            mime="application/geo+json", 
            use_container_width=True
        )
        
    with col_map:
        st.subheader("3. Peta WebGIS (Task 3 & 4)")
        
        # Gunakan titik tengah poligon asal untuk fokus peta
        gdf_wgs84 = gdf.to_crs(epsg=4326)
        pusat_wgs84 = gdf_wgs84.centroid
        lat_tengah = pusat_wgs84.y.iloc[0]
        lon_tengah = pusat_wgs84.x.iloc[0]
        
        # Bina peta Folium
        m = folium.Map(location=[lat_tengah, lon_tengah], zoom_start=18, control_scale=True, tiles=None, max_zoom=24)
        
        # TASK 3 & 4: Overlay Satelit (Google Hybrid)
        if show_sat:
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
                attr='Google Hybrid',
                name='Google Satellite',
                max_zoom=24,
                max_native_zoom=21
            ).add_to(m)
        else:
            folium.TileLayer('OpenStreetMap').add_to(m)
            
        # Masukkan poligon
        style_function = lambda x: {'fillColor': '#0000ff', 'color': '#0000ff', 'weight': 3, 'fillOpacity': 0.3}
        folium.GeoJson(gdf_wgs84, style_function=style_function, name="Sempadan").add_to(m)
        
        # Label (Task 4)
        for i in range(len(df)):
            e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
            stn_name = str(df.iloc[i]['STN'])
            
            # --- CONVERT TITIK LABEL KE WGS 84 ---
            pt = gpd.GeoSeries([Point(e1, n1)], crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
            pt_lat = pt.y.iloc[0]
            pt_lon = pt.x.iloc[0]
            
            if show_stn:
                folium.CircleMarker(
                    location=[pt_lat, pt_lon], radius=4, color='red', fill=True, fill_color='red'
                ).add_to(m)
                folium.Marker(
                    location=[pt_lat, pt_lon],
                    icon=folium.DivIcon(html=f'<div style="font-weight:bold; color:white; text-shadow: 1px 1px 2px black; font-size: 14pt;">{stn_name}</div>')
                ).add_to(m)
            
            if show_bearing:
                e2, n2 = df.iloc[(i+1) % len(df)]['E'], df.iloc[(i+1) % len(df)]['N']
                j, b = kira_bering_jarak(e1, n1, e2, n2)
                
                mid_e, mid_n = (e1 + e2)/2, (n1 + n2)/2
                
                # --- CONVERT TITIK BERING/JARAK KE WGS 84 ---
                mid_pt = gpd.GeoSeries([Point(mid_e, mid_n)], crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
                mid_lat, mid_lon = mid_pt.y.iloc[0], mid_pt.x.iloc[0]
                
                label_text = f"{j:.3f}m<br>{format_bering(b)}"
                folium.Marker(
                    location=[mid_lat, mid_lon],
                    icon=folium.DivIcon(html=f'<div style="color:yellow; text-shadow: 1px 1px 2px black; font-size: 10pt; text-align:center; width: 100px; margin-left:-50px;">{label_text}</div>')
                ).add_to(m)

        # Render peta di Streamlit
        st_folium(m, use_container_width=True, height=600)
