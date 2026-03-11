import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
import folium
from streamlit_folium import st_folium
import math
import io

# Konfigurasi Halaman
st.set_page_config(page_title="Sistem WebGIS Ukur", layout="wide", page_icon="🗺️")

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
    
    # EPSG sangat penting untuk Easting/Northing overlay ke Satelit
    epsg_code = st.text_input("Kod EPSG Sistem Koordinat Anda", value="3386", 
                              help="Contoh: 3386 untuk Perak Cassini, 3168 untuk Semenanjung MRSO, 32647 untuk UTM 47N")

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
                df_display['Jarak ke Stesen Seterusnya (m)'] = jarak_list
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
    
    # Bina Poligon (Tutup stesen terakhir ke stesen pertama)
    poly_geom = Polygon(zip(df['E'], df['N']))
    
    # Bina GeoDataFrame menggunakan Easting/Northing
    gdf = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_code}")
    
    # Kira keluasan (dalam unit meter jika E/N dalam meter)
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
        # TASK 2: Export Data GeoJSON & Shapefile
        st.write("**Eksport Data (Task 2):**")
        
        # Tukar CRS ke lat/lon (WGS84) untuk standard GeoJSON
        gdf_wgs84 = gdf.to_crs(epsg=4326)
        geojson_data = gdf_wgs84.to_json()
        
        st.download_button("💾 Muat Turun GeoJSON", data=geojson_data, file_name="poligon.geojson", mime="application/geo+json", use_container_width=True)
        
        st.info("Nota: Untuk Shapefile, sistem biasanya mengeksport dalam format ZIP, GeoJSON lebih mesra web.")
        
    with col_map:
        st.subheader("3. Peta WebGIS (Task 3 & 4)")
        
        # Dapatkan titik tengah untuk letak kamera peta
        pusat_wgs84 = gdf_wgs84.centroid
        lat_tengah = pusat_wgs84.y.iloc[0]
        lon_tengah = pusat_wgs84.x.iloc[0]
        
        # Mula bina peta Folium
        m = folium.Map(location=[lat_tengah, lon_tengah], zoom_start=18, control_scale=True)
        
        # TASK 3 & 4: Overlay Satelit
        if show_sat:
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                attr='Google Satellite',
                name='Google Satellite',
                max_zoom=20
            ).add_to(m)
        else:
            folium.TileLayer('OpenStreetMap').add_to(m)
            
        # Masukkan poligon ke dalam peta
        style_function = lambda x: {'fillColor': '#0000ff', 'color': '#0000ff', 'weight': 3, 'fillOpacity': 0.3}
        folium.GeoJson(gdf_wgs84, style_function=style_function, name="Sempadan").add_to(m)
        
        # Tambah Marker untuk Label (Task 4)
        for i in range(len(df)):
            e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
            stn_name = df.iloc[i]['STN']
            
            # Tukar setiap koordinat E/N ke WGS84 untuk plot di Folium
            pt = gpd.GeoSeries([Point(e1, n1)], crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
            pt_lat = pt.y.iloc[0]
            pt_lon = pt.x.iloc[0]
            
            # Togol Label Stesen
            if show_stn:
                folium.CircleMarker(
                    location=[pt_lat, pt_lon], radius=4, color='red', fill=True, fill_color='red'
                ).add_to(m)
                folium.Marker(
                    location=[pt_lat, pt_lon],
                    icon=folium.DivIcon(html=f'<div style="font-weight:bold; color:white; text-shadow: 1px 1px 2px black; font-size: 14pt;">{stn_name}</div>')
                ).add_to(m)
            
            # Togol Bering & Jarak
            if show_bearing:
                e2, n2 = df.iloc[(i+1) % len(df)]['E'], df.iloc[(i+1) % len(df)]['N']
                j, b = kira_bering_jarak(e1, n1, e2, n2)
                
                # Cari titik tengah antara dua stesen untuk letak teks bering/jarak
                mid_e, mid_n = (e1 + e2)/2, (n1 + n2)/2
                mid_pt = gpd.GeoSeries([Point(mid_e, mid_n)], crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
                mid_lat, mid_lon = mid_pt.y.iloc[0], mid_pt.x.iloc[0]
                
                label_text = f"{j:.3f}m<br>{format_bering(b)}"
                folium.Marker(
                    location=[mid_lat, mid_lon],
                    icon=folium.DivIcon(html=f'<div style="color:yellow; text-shadow: 1px 1px 2px black; font-size: 10pt; text-align:center; width: 100px; margin-left:-50px;">{label_text}</div>')
                ).add_to(m)

        # Render peta di Streamlit
        st_folium(m, use_container_width=True, height=600)
