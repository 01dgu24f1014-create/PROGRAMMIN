with col_map:
        st.subheader("3. Peta WebGIS (Task 3 & 4)")
        
        # Dapatkan titik tengah untuk letak kamera peta
        pusat_wgs84 = gdf_wgs84.centroid
        lat_tengah = pusat_wgs84.y.iloc[0]
        lon_tengah = pusat_wgs84.x.iloc[0]
        
        # Mula bina peta Folium (TUTUP peta lalai dengan tiles=None)
        m = folium.Map(location=[lat_tengah, lon_tengah], zoom_start=18, control_scale=True, tiles=None)
        
        # TASK 3 & 4: Overlay Satelit
        if show_sat:
            # Guna 'lyrs=y' untuk Google Hybrid (Satelit + Teks Label Tempat)
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
                attr='Google Hybrid',
                name='Google Satellite',
                max_zoom=20
            ).add_to(m)
        else:
            # Peta biasa jika satelit di-off
            folium.TileLayer('OpenStreetMap').add_to(m)
            
        # Masukkan poligon ke dalam peta
        style_function = lambda x: {'fillColor': '#0000ff', 'color': '#0000ff', 'weight': 3, 'fillOpacity': 0.3}
        folium.GeoJson(gdf_wgs84, style_function=style_function, name="Sempadan").add_to(m)
        
        # Tambah Marker untuk Label (Task 4)
        for i in range(len(df)):
            e1, n1 = df.iloc[i]['E'], df.iloc[i]['N']
            stn_name = str(df.iloc[i]['STN'])
            
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
