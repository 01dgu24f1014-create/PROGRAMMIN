import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point, LineString
import folium
import math
import time
import os
import webbrowser

# ==========================================
# --- KONFIGURASI HALAMAN DESKTOP ---
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SistemWebGISDesktop(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistem WebGIS Ukur - Desktop Version")
        self.geometry("1100x700")

        # --- SISTEM LOG MASUK ---
        self.users_db = {
            "admin": {"name": "MUHAMMAD UMAR BIN ZULKARNAIN", "password": "12345"},
            "fakhrulis": {"name": "FAKHRULIS", "password": "12345"},
            "Aniqs": {"name": "ANIQS", "password": "12345"}
        }
        self.logged_in = False
        self.login_attempts = 0
        self.lockout_time = 0
        self.current_user = ""
        
        # Pembolehubah GIS
        self.df = None
        self.epsg_code = "4390"

        self.tunjuk_skrin_login()

    # --- FUNGSI PENGIRAAN BERING & JARAK ---
    def kira_bering_jarak(self, e1, n1, e2, n2):
        de = e2 - e1
        dn = n2 - n1
        jarak = math.sqrt(de**2 + dn**2)
        bering = math.degrees(math.atan2(de, dn))
        if bering < 0:
            bering += 360
        return jarak, bering

    def format_bering(self, deg):
        d = int(deg)
        m = int((deg - d) * 60)
        s = (deg - d - m/60) * 3600
        return f"{d}° {m}' {s:.0f}\""

    # ==========================================
    # --- SKRIN LOG MASUK ---
    # ==========================================
    def tunjuk_skrin_login(self):
        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self.frame_login, text="🔒 Log Masuk Sistem WebGIS", font=("Arial Black", 20)).pack(pady=20, padx=40)
        
        self.entry_id = ctk.CTkEntry(self.frame_login, placeholder_text="ID Pengguna", width=250)
        self.entry_id.pack(pady=10)
        
        self.entry_pass = ctk.CTkEntry(self.frame_login, placeholder_text="Kata Laluan", show="*", width=250)
        self.entry_pass.pack(pady=10)
        
        ctk.CTkButton(self.frame_login, text="Log Masuk", command=self.semak_login).pack(pady=20)

    def semak_login(self):
        if self.login_attempts >= 3:
            time_passed = time.time() - self.lockout_time
            if time_passed < 40:
                baki_masa = int(40 - time_passed)
                messagebox.showerror("Dikunci", f"🚫 Sistem dikunci. Sila tunggu {baki_masa} saat lagi.")
                return
            else:
                self.login_attempts = 0 

        user_id = self.entry_id.get()
        password = self.entry_pass.get()

        if user_id in self.users_db and password == self.users_db[user_id]['password']:
            self.logged_in = True
            self.current_user = user_id
            self.login_attempts = 0
            self.frame_login.destroy()
            self.tunjuk_skrin_utama()
        else:
            self.login_attempts += 1
            if self.login_attempts >= 3:
                self.lockout_time = time.time()
                messagebox.showerror("Dikunci", "3 percubaan gagal. Sistem dikunci selama 40 saat.")
            else:
                baki = 3 - self.login_attempts
                messagebox.showwarning("Ralat", f"ID atau Kata Laluan tidak sah. Baki percubaan: {baki}")

    # ==========================================
    # --- SKRIN UTAMA ---
    # ==========================================
    def tunjuk_skrin_utama(self):
        user_full_name = self.users_db[self.current_user]['name']

        # --- MENU TEPI (SIDEBAR) ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        ctk.CTkLabel(self.sidebar, text=f"👋 {user_full_name}", font=("Arial", 16, "bold")).pack(pady=20)
        
        ctk.CTkLabel(self.sidebar, text="🎛️ Kawalan Visual", font=("Arial", 14)).pack(pady=10)
        self.saiz_marker = ctk.CTkSlider(self.sidebar, from_=1, to=50)
        self.saiz_marker.set(22)
        self.saiz_marker.pack(pady=10, padx=20)
        ctk.CTkLabel(self.sidebar, text="Saiz Marker").pack()

        self.tahap_zoom = ctk.CTkSlider(self.sidebar, from_=10, to=24)
        self.tahap_zoom.set(19)
        self.tahap_zoom.pack(pady=10, padx=20)
        ctk.CTkLabel(self.sidebar, text="Tahap Zoom").pack()

        ctk.CTkButton(self.sidebar, text="🚪 Log Keluar", fg_color="#C62828", hover_color="#B71C1C", command=self.log_keluar).pack(side="bottom", pady=20)

        # --- RUANG KANAN (MAIN CONTENT) ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(self.main_frame, text="SISTEM SURVEY LOT", font=("Arial Black", 28)).pack(pady=10)
        ctk.CTkLabel(self.main_frame, text="Politeknik Ungku Omar | Jabatan Kejuruteraan Awam", font=("Georgia", 14, "italic")).pack()

        # Butang Muat Naik
        ctk.CTkButton(self.main_frame, text="📂 Muat Naik Fail CSV", font=("Arial", 14), command=self.muat_naik_csv).pack(pady=20)
        
        # Paparan Info Data
        self.lbl_info = ctk.CTkLabel(self.main_frame, text="", font=("Arial", 14))
        self.lbl_info.pack(pady=10)

        # Butang Buka Peta
        self.btn_peta = ctk.CTkButton(self.main_frame, text="🌍 Buka Peta WebGIS", font=("Arial", 14), state="disabled", command=self.jana_folium)
        self.btn_peta.pack(pady=10)

    def log_keluar(self):
        self.sidebar.destroy()
        self.main_frame.destroy()
        self.logged_in = False
        self.tunjuk_skrin_login()

    # ==========================================
    # --- PROSES DATA & FOLIUM ---
    # ==========================================
    def muat_naik_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not filepath: return

        try:
            self.df = pd.read_csv(filepath)
            if all(col in self.df.columns for col in ['STN', 'E', 'N']):
                
                # Kira Luas dan Perimeter
                poly_geom = Polygon(zip(self.df['E'], self.df['N']))
                gdf = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{self.epsg_code}")
                keluasan = gdf.area.iloc[0]
                
                jarak_total = sum([self.kira_bering_jarak(self.df.iloc[i]['E'], self.df.iloc[i]['N'], 
                                                          self.df.iloc[(i+1)%len(self.df)]['E'], 
                                                          self.df.iloc[(i+1)%len(self.df)]['N'])[0] for i in range(len(self.df))])
                
                self.lbl_info.configure(text=f"✅ Data Dimuat Naik!\nBilangan Stesen: {len(self.df)}\nLuas: {keluasan:.3f} m²\nPerimeter: {jarak_total:.3f} m")
                self.btn_peta.configure(state="normal")
                messagebox.showinfo("Berjaya", "Data CSV berjaya diproses.")
            else:
                messagebox.showerror("Ralat", "Fail CSV mesti ada kolum 'STN', 'E', dan 'N'.")
        except Exception as e:
            messagebox.showerror("Ralat", f"Ralat membaca fail: {e}")

    def jana_folium(self):
        poly_geom = Polygon(zip(self.df['E'], self.df['N']))
        gdf = gpd.GeoDataFrame(index=[0], geometry=[poly_geom], crs=f"EPSG:{self.epsg_code}")
        gdf_wgs84 = gdf.to_crs(epsg=4326)
        lat_tengah, lon_tengah = gdf_wgs84.centroid.y.iloc[0], gdf_wgs84.centroid.x.iloc[0]

        m = folium.Map(location=[lat_tengah, lon_tengah], zoom_start=int(self.tahap_zoom.get()))
        
        folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Satelit').add_to(m)

        folium.GeoJson(
            gdf_wgs84, 
            style_function=lambda x: {'fillColor': '#A020F0', 'color': 'none', 'fillOpacity': 0.3}
        ).add_to(m)

        for i in range(len(self.df)):
            e1, n1 = self.df.iloc[i]['E'], self.df.iloc[i]['N']
            stn_name = str(self.df.iloc[i]['STN'])
            pt = gpd.GeoSeries([Point(e1, n1)], crs=f"EPSG:{self.epsg_code}").to_crs(epsg=4326)
            lat, lon = pt.y.iloc[0], pt.x.iloc[0]

            folium.CircleMarker(
                location=[lat, lon], radius=self.saiz_marker.get() / 4, color='red', fill=True, fill_color='red',
                tooltip=f"Stesen: {stn_name}"
            ).add_to(m)

        laluan_fail = os.path.join(os.getcwd(), "peta_desktop.html")
        m.save(laluan_fail)
        webbrowser.open(f"file://{laluan_fail}")

if __name__ == "__main__":
    app = SistemWebGISDesktop()
    app.mainloop()
