import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Visualisasi Data Ukur", layout="centered")

st.title("🗺️ Paparan Poligon Data Ukur")
st.write("Muat naik fail CSV anda untuk melihat bentuk poligon koordinat.")

# 1. Bahagian Muat Naik Fail
uploaded_file = st.file_uploader("Pilih fail CSV (E, N)", type=["csv"])

if uploaded_file is not None:
    # Membaca data
    df = pd.read_csv(uploaded_file)
    
    st.subheader("Data Mentah")
    st.write(df)

    # Memastikan kolum yang diperlukan wujud
    if 'E' in df.columns and 'N' in df.columns:
        
        # 2. Menutup Poligon (Menyambung titik akhir ke titik awal)
        # Kita salin baris pertama dan letak di hujung dataframe
        df_poly = pd.concat([df, df.iloc[[0]]], ignore_index=True)

        # 3. Mencipta Plot menggunakan Plotly
        fig = go.Figure()

        # Garisan Poligon
        fig.add_trace(go.Scatter(
            x=df_poly['E'], 
            y=df_poly['N'],
            mode='lines+markers+text',
            fill="toself", # Mengisi warna di dalam poligon
            text=df_poly['STN'],
            textposition="top center",
            name="Sempadan",
            line=dict(color='RoyalBlue', width=2)
        ))

        # Kemaskan susun atur (Layout)
        fig.update_layout(
            xaxis_title="Easting (E)",
            yaxis_title="Northing (N)",
            yaxis=dict(scaleanchor="x", scaleratio=1), # Memastikan nisbah 1:1 (penting untuk geometri)
            showlegend=False,
            width=700,
            height=700
        )

        # 4. Paparkan dalam Streamlit
        st.subheader("Visualisasi Poligon")
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.error("Ralat: Fail CSV mesti mempunyai kolum 'E' dan 'N'.")

else:
    st.info("Sila muat naik fail 'data ukur.csv' untuk bermula.")