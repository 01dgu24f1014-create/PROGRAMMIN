import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point, LineString
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
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
            if user_id == "admin" and password == "12345":
                st.session_state['logged_in'] = True
                st.rerun() 
            else:
                st.error("Ralat: ID Pengguna atau Kata Laluan tidak sah. Cuba lagi.")
    
    st.stop()

# Butang Log Keluar di menu tepi
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
    
    epsg_code = st.text_input("Kod EPSG Sistem Koordinat Anda", value="4390", 
                              help="Lalai: 4390 untuk Kertau / Johor Grid. Ubah mengikut keperluan.")

with col2:
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            if 'E' in df.columns and 'N' in df.columns and 'STN' in df.columns:
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
    # --- PROSES GEOPANDAS ---
    poly_geom = Polygon(zip(df['E'], df['N']))
    gdf = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{epsg_code}")
    keluasan = gdf.area.iloc[0]
    perimeter = sum(df_display['Jarak (m)']) # Kira Perimeter (Jumlah Jarak)
    
    col_tools, col_map = st.columns([1, 3])
    
    with col_tools:
        st.subheader("2. Kawalan & Analisis")
        
        if st.button("📏 Kira Keluasan Auto", type="primary", use_container_width=True):
            st.success(f"**Luas Poligon:** {keluasan:.3f} meter persegi")
        
        st.markdown("---")
        st.write("**Togol Visualisasi Peta GIS:**")
        show_sat = st.checkbox("🌍 Paparkan Imej Satelit", value=True)
        show_stn = st.checkbox("🏷️ Paparkan Label Stesen", value=True)
        show_bearing = st.checkbox("📐 Paparkan Bering & Jarak", value=True)
        
        st.markdown("---")
        st.write("**Eksport Data:**")
        
        features_list = []
        features_list.append({"geometry": poly_geom, "Kategori": "Lot", "Label": "Poligon", "Jarak": "", "Bering": ""})
        
        for i in range(len(df)):
            e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
            e2, n2 = df.iloc[(i+1) % len(df)]['E'], df.iloc[(i+1) % len(df)]['N']
            stn_name = str(df.iloc[i]['STN'])
            j, b = kira_bering_jarak(e1, n1, e2, n2)
            
            features_list.append({"geometry": Point(e1, n1), "Kategori": "Stesen", "Label": stn_name, "Jarak": "", "Bering": ""})
            features_list.append({"geometry": LineString([(e1, n1), (e2, n2)]), "Kategori": "Sempadan", "Label": stn_name, "Jarak": f"{j:.3f}m", "Bering": format_bering(b)})
            
            mid_e, mid_n = (e1 + e2)/2, (n1 + n2)/2
            features_list.append({"geometry": Point(mid_e, mid_n), "Kategori": "Label", "Label": f"{j:.3f}m | {format_bering(b)}", "Jarak": f"{j:.3f}m", "Bering": format_bering(b)})

        gdf_export = gpd.GeoDataFrame(features_list, crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
        
        st.download_button(
            label="💾 Muat Turun GeoJSON", 
            data=gdf_export.to_json(), 
            file_name="data_gis.geojson", 
            mime="application/geo+json", 
            use_container_width=True
        )
        
    with col_map:
        st.subheader("3. Analisis Ruangan (Spatial Analysis)")
        
        # BINA TAB (TEB) UNTUK TUKAR-TUKAR PAPARAN
        tab_plotly, tab_gis = st.tabs(["📊 Pelan 2D & Metrik", "🌍 Peta WebGIS (Satelit)"])
        
        # ==========================================
        # --- PAPARAN TAB 1: PLOTLY (SEPERTI GAMBAR KANAN) ---
        # ==========================================
        with tab_plotly:
            # Bahagian Kad Metrik
            m1, m2, m3 = st.columns(3)
            m1.metric("Luas", f"{keluasan:.2f} m²")
            m2.metric("Perimeter", f"{perimeter:.2f} m")
            m3.metric("Bilangan Stesen", f"{len(df)}")
            
            # Bina Figure Plotly
            fig = go.Figure()
            
            # 1. Garisan Sempadan (Tutup Poligon)
            e_closed = list(df['E']) + [df['E'].iloc[0]]
            n_closed = list(df['N']) + [df['N'].iloc[0]]
            
            fig.add_trace(go.Scatter(
                x=e_closed, y=n_closed, 
                mode='lines+markers',
                line=dict(color='black', width=2),
                marker=dict(color='red', size=12),
                name='Sempadan'
            ))
            
            # 2. Masukkan Label Stesen
            for i in range(len(df)):
                fig.add_annotation(
                    x=df['E'].iloc[i], y=df['N'].iloc[i],
                    text=f"<b>{df['STN'].iloc[i]}</b>",
                    showarrow=False,
                    xshift=15, yshift=15,
                    font=dict(color="blue", size=16)
                )
                
            # 3. Masukkan Label Bering & Jarak
            for i in range(len(df)):
                e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
                e2, n2 = df.iloc[(i+1) % len(df)]['E'], df.iloc[(i+1) % len(df)]['N']
                mid_e, mid_n = (e1 + e2)/2, (n1 + n2)/2
                
                j = df_display['Jarak (m)'].iloc[i]
                b = df_display['Bering'].iloc[i]
                
                # Kira sudut teks supaya selari dengan garisan
                dx, dy = e2 - e1, n2 - n1
                angle = math.degrees(math.atan2(dy, dx))
                if angle > 90: angle -= 180
                elif angle < -90: angle += 180
                
                fig.add_annotation(
                    x=mid_e, y=mid_n,
                    text=f"<b>{b}<br>{j:.3f}m</b>",
                    showarrow=False,
                    textangle=-angle, # Sengetkan teks
                    font=dict(color="darkred", size=12)
                )

            # 4. Kotak LUAS berwarna Hijau di tengah poligon
            pusat = poly_geom.centroid
            fig.add_annotation(
                x=pusat.x, y=pusat.y,
                text=f"<b>LUAS<br>{keluasan:.2f} m²</b>",
                showarrow=False,
                font=dict(color="green", size=18),
                bgcolor="white",
                bordercolor="green",
                borderwidth=2,
                borderpad=5
            )

            # 5. Kemaskan Paparan Grid (Aspect Ratio = 1:1)
            fig.update_layout(
                yaxis=dict(scaleanchor="x", scaleratio=1, showgrid=True, gridcolor='lightgrey', griddash='dot'),
                xaxis=dict(showgrid=True, gridcolor='lightgrey', griddash='dot'),
                plot_bgcolor='white',
                margin=dict(l=10, r=10, t=30, b=10),
                height=500
            )

            # Keluarkan Plotly ke Streamlit
            st.plotly_chart(fig, use_container_width=True)

        
        # ==========================================
        # --- PAPARAN TAB 2: FOLIUM WEBGIS (GAMBAR KIRI) ---
        # ==========================================
        with tab_gis:
            gdf_wgs84 = gdf.to_crs(epsg=4326)
            lat_tengah, lon_tengah = gdf_wgs84.centroid.y.iloc[0], gdf_wgs84.centroid.x.iloc[0]
            
            m = folium.Map(location=[lat_tengah, lon_tengah], zoom_start=18, control_scale=True, max_zoom=24)
            
            if show_sat:
                folium.TileLayer(
                    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google Hybrid', max_zoom=24, max_native_zoom=21
                ).add_to(m)
            else:
                folium.TileLayer('OpenStreetMap').add_to(m)
                
            folium.GeoJson(gdf_wgs84, style_function=lambda x: {'fillColor': '#0000ff', 'color': '#0000ff', 'weight': 3, 'fillOpacity': 0.3}).add_to(m)
            
            for i in range(len(df)):
                e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
                stn_name = str(df.iloc[i]['STN'])
                pt = gpd.GeoSeries([Point(e1, n1)], crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
                pt_lat, pt_lon = pt.y.iloc[0], pt.x.iloc[0]
                
                if show_stn:
                    folium.CircleMarker(location=[pt_lat, pt_lon], radius=4, color='red', fill=True, fill_color='red').add_to(m)
                    folium.Marker(location=[pt_lat, pt_lon], icon=folium.DivIcon(html=f'<div style="font-weight:bold; color:white; text-shadow: 1px 1px 2px black; font-size: 14pt;">{stn_name}</div>')).add_to(m)
                
                if show_bearing:
                    e2, n2 = df.iloc[(i+1) % len(df)]['E'], df.iloc[(i+1) % len(df)]['N']
                    j, b = kira_bering_jarak(e1, n1, e2, n2)
                    mid_e, mid_n = (e1 + e2)/2, (n1 + n2)/2
                    mid_pt = gpd.GeoSeries([Point(mid_e, mid_n)], crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
                    mid_lat, mid_lon = mid_pt.y.iloc[0], mid_pt.x.iloc[0]
                    folium.Marker(location=[mid_lat, mid_lon], icon=folium.DivIcon(html=f'<div style="color:yellow; text-shadow: 1px 1px 2px black; font-size: 10pt; text-align:center; width: 100px; margin-left:-50px;">{j:.3f}m<br>{format_bering(b)}</div>')).add_to(m)

            st_folium(m, use_container_width=True, height=500)
