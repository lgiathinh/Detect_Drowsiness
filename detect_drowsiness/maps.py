import folium
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
import setting


setting.init()
class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.combine_map = None
        
        self.marker_count = 0
        self.setWindowTitle("Map Viewer")
        self.map_file = "google_map.html"
        self.locations_dms = {
            'Ho Chi Minh City': (10, 51.15604, "'N'", 106, 45.58957, "'E'"),
        }
        self.create_map()
        self.web_view = QWebEngineView()
        self.web_view.load("http://localhost:8000/google_map.html")

        # Layout
        self.container = QWidget()
        layout = QVBoxLayout(self.container)
        layout.addWidget(self.web_view)
        self.setCentralWidget(self.container)
            
    def create_map(self):
        def dms_to_decimal(degrees, minutes, direction):
            decimal = degrees + (minutes / 60)
            if direction in ['S', 'W']:
                decimal = -decimal
            return decimal
        
        # Chuyển đổi sang tọa độ Decimal Degrees
        locations_decimal = {
            city: (
                dms_to_decimal(lat_deg, lat_min, lat_dir),
                dms_to_decimal(lon_deg, lon_min, lon_dir)
            )
            for city, (lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir) in self.locations_dms.items()
        }

        self.combine_map = folium.Map(location=[10.7769, 106.7009], zoom_start=10)
        print(locations_decimal)
        for index, (location, coordinates) in enumerate(locations_decimal.items(), start=1):
            folium.Marker(
                location=coordinates,
                icon=folium.DivIcon(
                    html=f"""<div style="font-size: 12px; color: white; background-color: blue; border-radius: 50%; 
                            width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">
                            {index}</div>"""
                ),
                popup=f"{location}"
            ).add_to(self.combine_map)

        self.combine_map.save(self.map_file)

    def dms_to_dec(self, deg, min, dir):
        dec = deg + (min/60)
        if dir in ['S','W']:
            dec = -dec
        return dec
    
    
    def add_location(self,lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir):
        self.locations_decimal = (lat_deg, lat_min, lat_dir,lon_deg, lon_min, lon_dir)
        self.locations_dms[f"Coordinates_{self.marker_count}"] = self.locations_decimal
        print(self.locations_dms)
        self.marker_count += 1
        self.create_map()
        print("Have created new location")