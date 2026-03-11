st.markdown("---")
        # TASK 2: Export Data to GIS
        st.write("**Eksport Data (Task 2):**")
        
        # Import LineString untuk buat garisan (wajib untuk garisan sempadan)
        from shapely.geometry import LineString
        
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
