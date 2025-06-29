import sys
import folium
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Viewer")

        # Tạo bản đồ Folium
        self.create_map()

        # Giao diện Qt
        self.web_view = QWebEngineView()
        self.web_view.load("http://localhost:8000/google_map.html")  # Dùng máy chủ cục bộ

        # Layout
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.web_view)
        self.setCentralWidget(container)
        
    

    def create_map(self):
        # Danh sách thành phố với tọa độ DMS
        locations_dms = {
            'New York': (40, 42.48, 'N', 74, 0.36, 'W'),
            'Los Angeles': (34, 3.132, 'N', 118, 14.622, 'W'),
            'Chicago': (41, 52.686, 'N', 87, 37.764, 'W'),
            'Ho Chi Minh City': (10, 51.15604, 'N', 106, 45.58957, 'E')
        }
        def dms_to_decimal(degrees, minutes, direction):
            decimal = degrees + (minutes / 60)
            if direction in ['S', 'W']:  # Nếu là phía Nam hoặc Tây, giá trị âm
                decimal = -decimal
            return decimal
        
        # Chuyển đổi sang tọa độ Decimal Degrees
        locations_decimal = {
            city: (
                dms_to_decimal(lat_deg, lat_min, lat_dir),
                dms_to_decimal(lon_deg, lon_min, lon_dir)
            )
            for city, (lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir) in locations_dms.items()
        }

        # Tạo bản đồ
        combine_map = folium.Map(location=[10.8512604, 106.759825], zoom_start=10)

        # Thêm điểm đánh dấu
        for index, (location, coordinates) in enumerate(locations_decimal.items(), start=1):
            folium.Marker(
                location=coordinates,
                icon=folium.DivIcon(
                    html=f"""<div style="font-size: 12px; color: white; background-color: blue; border-radius: 50%; 
                            width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">
                            {index}</div>"""
                ),
                popup=f"{location}"
            ).add_to(combine_map)

        # Lưu bản đồ ra file
        self.map_file = "google_map.html"
        combine_map.save(self.map_file)


# Máy chủ cục bộ
def run_server():
    handler = SimpleHTTPRequestHandler
    with TCPServer(("", 8000), handler) as httpd:
        print("Serving at port 8000")
        httpd.serve_forever()
