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
# Simpan pangkalan data pengguna sementara
if 'users_db' not in st.session_state:
    st.session_state['users_db'] = {
        "admin": {"name": "MUHAMMAD UMAR BIN ZULKARNAIN", "password": "12345"},
        "fakhrulis": {"name": "FAKHRULIS", "password": "12345"},
        "Aniqs": {"name": "ANIQS", "password": "12345"}
    }

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
            # Semak dengan database pengguna
            if user_id in st.session_state['users_db'] and password == st.session_state['users_db'][user_id]['password']:
                st.session_state['logged_in'] = True
                st.session_state['current_user'] = user_id # Simpan ID yang sedang login
                st.rerun() 
            else:
                st.error("Ralat: ID Pengguna atau Kata Laluan tidak sah. Cuba lagi.")
    
    st.stop()

# ==========================================
# --- MENU TEPI (SIDEBAR) ---
# ==========================================
# Ambil nama penuh berdasarkan ID yang sedang login
current_user = st.session_state['current_user']
user_full_name = st.session_state['users_db'][current_user]['name']

st.sidebar.markdown(f"### 👋 {user_full_name}")
st.sidebar.markdown("---")

# --- KAWALAN UI ---
saiz_marker = st.sidebar.slider("Saiz Marker Stesen", min_value=1, max_value=50, value=22)
saiz_font = st.sidebar.slider("Saiz Bearing/Jarak", min_value=5, max_value=30, value=12)
tahap_zoom = st.sidebar.slider("Tahap Zoom", min_value=10, max_value=24, value=19)
warna_poligon = st.sidebar.color_picker("Warna Poligon", "#A020F0")

st.sidebar.markdown("---")

# --- MENU TUKAR KATA LALUAN (DI BAWAH) ---
with st.sidebar.expander("🔑 Tukar Kata Laluan"):
    new_password = st.text_input("Kata Laluan Baru", type="password")
    if st.button("Simpan"):
        if new_password:
            st.session_state['users_db'][current_user]['password'] = new_password
            st.success("Berjaya ditukar!")
        else:
            st.warning("Masukkan kata laluan.")

st.sidebar.markdown("<br>", unsafe_allow_html=True) # Jarak kosong

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state['logged_in'] = False
    st.rerun()

# ==========================================
# --- KOD ASAL WEBGIS BERMULA DI SINI ---
# ==========================================

# --- REKA BENTUK CUSTOM HEADER (TAJUK) ---
custom_header = """
<style>
.header-container {
    background-color: #121826;
    padding: 50px 30px 30px 30px;
    border-radius: 15px;
    text-align: center;
    position: relative;
    border-bottom: 4px solid #F6D365;
    margin-bottom: 30px;
    box-shadow: 0px 5px 15px rgba(0,0,0,0.2);
}
.main-title {
    color: #FFFFFF;
    font-size: 45px;
    font-family: 'Arial Black', sans-serif;
    font-weight: 900;
    margin: 0;
    letter-spacing: 1.5px;
}
.sub-title {
    color: #E2E8F0;
    font-size: 18px;
    font-style: italic;
    font-family: 'Georgia', serif;
    margin-top: 10px;
    margin-bottom: 20px;
}
.developer-credit {
    position: absolute;
    bottom: 15px;
    right: 30px;
    color: #94A3B8;
    font-size: 12px;
    font-family: 'Courier New', monospace;
    font-weight: bold;
    letter-spacing: 2px;
}
</style>

<div class="header-container">
    <h1 class="main-title">SISTEM SURVEY LOT</h1>
    <p class="sub-title">Politeknik Ungku Omar | Jabatan Kejuruteraan Awam</p>
    <div class="developer-credit">DEVELOPED BY: MUHAMMAD UMAR BIN ZULKARNAIN</div>
</div>
"""

st.markdown(custom_header, unsafe_allow_html=True)
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
    perimeter = sum(df_display['Jarak (m)']) 
    
    col_tools, col_map = st.columns([1, 3])
    
    with col_tools:
        st.subheader("2. Kawalan & Analisis")
        
        if st.button("📏 Kira Keluasan Auto", type="primary", use_container_width=True):
            st.success(f"**Luas Poligon:** {keluasan:.3f} meter persegi")
        
        st.markdown("---")
        st.write("**Togol Visualisasi Peta GIS:**")
        # Checkbox Imej Satelit dibuang kerana Layer Control telah ditambah pada peta
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
        tab_plotly, tab_gis = st.tabs(["📊 Pelan 2D & Metrik", "🌍 Peta WebGIS (Satelit)"])
        
        # ==========================================
        # --- PAPARAN TAB 1: PLOTLY (GAMBAR KANAN) ---
        # ==========================================
        with tab_plotly:
            m1, m2, m3 = st.columns(3)
            m1.metric("Luas", f"{keluasan:.2f} m²")
            m2.metric("Perimeter", f"{perimeter:.2f} m")
            m3.metric("Bilangan Stesen", f"{len(df)}")
            
            fig = go.Figure()
            
            e_closed = list(df['E']) + [df['E'].iloc[0]]
            n_closed = list(df['N']) + [df['N'].iloc[0]]
            stn_closed = list(df['STN']) + [df['STN'].iloc[0]]
            
            hover_texts = []
            for idx in range(len(e_closed)):
                if idx < len(df):
                    j = df_display['Jarak (m)'].iloc[idx]
                    b = df_display['Bering'].iloc[idx]
                    next_stn = df['STN'].iloc[(idx+1)%len(df)]
                    hover_texts.append(f"<b>Kategori:</b> Stesen<br><b>Label:</b> {stn_closed[idx]}<br><b>Koordinat:</b> {e_closed[idx]}, {n_closed[idx]}<br><b>Arah ke {next_stn}:</b> {j:.3f}m | {b}")
                else:
                    hover_texts.append(f"<b>Kategori:</b> Stesen<br><b>Label:</b> {stn_closed[idx]}<br><b>Koordinat:</b> {e_closed[idx]}, {n_closed[idx]}")

            fig.add_trace(go.Scatter(
                x=e_closed, y=n_closed, 
                mode='lines+markers',
                line=dict(color='black', width=2),
                marker=dict(color='red', size=saiz_marker), 
                name='Sempadan',
                text=hover_texts,
                hoverinfo='text'
            ))
            
            fig.add_trace(go.Scatter(
                x=e_closed, y=n_closed,
                fill='toself',
                fillcolor='rgba(0, 0, 255, 0.05)', 
                line=dict(color='rgba(255,255,255,0)'),
                name='Lot',
                text=f"<b>Kategori:</b> Lot Poligon<br><b>Luas:</b> {keluasan:.3f} m²<br><b>Perimeter:</b> {perimeter:.3f} m",
                hoverinfo='text'
            ))
            
            for i in range(len(df)):
                fig.add_annotation(
                    x=df['E'].iloc[i], y=df['N'].iloc[i],
                    text=f"<b>{df['STN'].iloc[i]}</b>",
                    showarrow=False, xshift=15, yshift=15,
                    font=dict(color="blue", size=16)
                )
                
            for i in range(len(df)):
                e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
                e2, n2 = df.iloc[(i+1) % len(df)]['E'], df.iloc[(i+1) % len(df)]['N']
                mid_e, mid_n = (e1 + e2)/2, (n1 + n2)/2
                j = df_display['Jarak (m)'].iloc[i]
                b = df_display['Bering'].iloc[i]
                
                dx, dy = e2 - e1, n2 - n1
                angle = math.degrees(math.atan2(dy, dx))
                if angle > 90: angle -= 180
                elif angle < -90: angle += 180
                
                fig.add_annotation(
                    x=mid_e, y=mid_n, text=f"<b>{b}<br>{j:.3f}m</b>", showarrow=False, textangle=-angle, font=dict(color="darkred", size=saiz_font)
                )

            pusat = poly_geom.centroid
            fig.add_annotation(
                x=pusat.x, y=pusat.y, text=f"<b>LUAS<br>{keluasan:.2f} m²</b>",
                showarrow=False, font=dict(color="green", size=18), bgcolor="white",
                bordercolor="green", borderwidth=2, borderpad=5
            )

            fig.update_layout(
                yaxis=dict(scaleanchor="x", scaleratio=1, showgrid=True, gridcolor='lightgrey', griddash='dot'),
                xaxis=dict(showgrid=True, gridcolor='lightgrey', griddash='dot'),
                plot_bgcolor='white', margin=dict(l=10, r=10, t=30, b=10), height=500,
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

        
        # ==========================================
        # --- PAPARAN TAB 2: FOLIUM WEBGIS (GAMBAR KIRI) ---
        # ==========================================
        with tab_gis:
            gdf_wgs84 = gdf.to_crs(epsg=4326)
            lat_tengah, lon_tengah = gdf_wgs84.centroid.y.iloc[0], gdf_wgs84.centroid.x.iloc[0]
            
            m = folium.Map(location=[lat_tengah, lon_tengah], zoom_start=tahap_zoom, control_scale=True, max_zoom=24, tiles=None)
            
            # --- TIGA JENIS LAYER PETA KAWALAN ---
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Hybrid (Satelit)', max_zoom=24, max_native_zoom=21
            ).add_to(m)
            
            folium.TileLayer(
                'OpenStreetMap', name='Peta Jalan (OSM)', max_zoom=24
            ).add_to(m)
            
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google', name='Google Map Biasa', max_zoom=24, max_native_zoom=21
            ).add_to(m)
            
            # Kumpulan layer untuk Data Ukur membolehkan ia di "on/off" dalam Layer Control
            data_survey_layer = folium.FeatureGroup(name="Data Survey")
            
            html_lot = f"<div style='font-family: Arial; font-size: 13px;'><b>Kategori:</b> Lot Poligon<br><b>Luas:</b> {keluasan:.3f} m²<br><b>Perimeter:</b> {perimeter:.3f} m</div>"
            folium.GeoJson(
                gdf_wgs84, 
                style_function=lambda x: {'fillColor': warna_poligon, 'color': 'none', 'fillOpacity': 0.3},
                tooltip=folium.Tooltip(html_lot)
            ).add_to(data_survey_layer) # Ditambah ke dalam group
            
            for i in range(len(df)):
                e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
                e2, n2 = df.iloc[(i+1) % len(df)]['E'], df.iloc[(i+1) % len(df)]['N']
                stn_name = str(df.iloc[i]['STN'])
                
                pt1 = gpd.GeoSeries([Point(e1, n1)], crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
                lat1, lon1 = pt1.y.iloc[0], pt1.x.iloc[0]
                
                pt2 = gpd.GeoSeries([Point(e2, n2)], crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
                lat2, lon2 = pt2.y.iloc[0], pt2.x.iloc[0]
                
                j, b = kira_bering_jarak(e1, n1, e2, n2)
                
                html_line = f"<div style='font-family: Arial; font-size: 13px;'><b>Kategori:</b> Sempadan<br><b>Label:</b> {stn_name}<br><b>Jarak:</b> {j:.3f}m<br><b>Bering:</b> {format_bering(b)}</div>"
                folium.PolyLine(
                    locations=[[lat1, lon1], [lat2, lon2]], 
                    color='#0000ff', weight=4, opacity=0.8,
                    tooltip=folium.Tooltip(html_line)
                ).add_to(data_survey_layer)
                
                if show_stn:
                    html_stn = f"<div style='font-family: Arial; font-size: 13px;'><b>Kategori:</b> Stesen<br><b>Label:</b> {stn_name}<br><b>E:</b> {e1}<br><b>N:</b> {n1}</div>"
                    
                    folium.CircleMarker(
                        location=[lat1, lon1], radius=saiz_marker / 4, color='red', fill=True, fill_color='red',
                        tooltip=folium.Tooltip(html_stn)
                    ).add_to(data_survey_layer)
                    
                    folium.Marker(
                        location=[lat1, lon1], 
                        icon=folium.DivIcon(html=f'<div style="font-weight:bold; color:white; text-shadow: 1px 1px 2px black; font-size: 14pt; margin-left:10px;">{stn_name}</div>'),
                        tooltip=folium.Tooltip(html_stn)
                    ).add_to(data_survey_layer)
                
                if show_bearing:
                    mid_e, mid_n = (e1 + e2)/2, (n1 + n2)/2
                    mid_pt = gpd.GeoSeries([Point(mid_e, mid_n)], crs=f"EPSG:{epsg_code}").to_crs(epsg=4326)
                    mid_lat, mid_lon = mid_pt.y.iloc[0], mid_pt.x.iloc[0]
                    
                    html_bering = f"<div style='font-family: Arial; font-size: 13px;'><b>Kategori:</b> Bering & Jarak<br><b>Jarak:</b> {j:.3f}m<br><b>Bering:</b> {format_bering(b)}</div>"
                    folium.Marker(
                        location=[mid_lat, mid_lon], 
                        icon=folium.DivIcon(html=f'<div style="color:yellow; text-shadow: 1px 1px 2px black; font-size: {saiz_font}pt; text-align:center; width: 100px; margin-left:-50px;">{j:.3f}m<br>{format_bering(b)}</div>'),
                        tooltip=folium.Tooltip(html_bering)
                    ).add_to(data_survey_layer)

            # Masukkan seluruh Kumpulan Data ke dalam Peta
            data_survey_layer.add_to(m)
            
            # --- TAMPILKAN MENU KAWALAN LAYER DI PENJURU ---
            folium.LayerControl(position='topright').add_to(m)

            st_folium(m, use_container_width=True, height=500)
