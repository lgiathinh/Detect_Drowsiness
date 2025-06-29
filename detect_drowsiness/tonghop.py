import sys
import threading
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout
from maps import MapWindow
from detect_drowsiness import EspCamWidget

class CombinedApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Combined Application")

        # Tạo các widget từ các module
        self.map_widget = MapWindow()
        self.esp_cam_widget = EspCamWidget()

        # Layout chính
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        # Thêm widget vào layout
        main_layout.addWidget(self.map_widget)
        main_layout.addWidget(self.esp_cam_widget)

        self.setCentralWidget(main_widget)

def run_local_server():
    # Hàm này chạy server cho maps.py (giả sử maps.py cần chạy HTTP server)
    from http.server import SimpleHTTPRequestHandler
    from socketserver import TCPServer

    handler = SimpleHTTPRequestHandler
    with TCPServer(("", 8000), handler) as httpd:
        print("Serving at port 8000")
        httpd.serve_forever()

from PySide6.QtGui import QGuiApplication

if __name__ == "__main__":
    # Chạy server cục bộ trong luồng riêng
    server_thread = threading.Thread(target=run_local_server, daemon=True)
    server_thread.start()

    # Khởi chạy ứng dụng Qt
    app = QApplication(sys.argv)

    # Lấy kích thước màn hình
    screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
    screen_width = screen_geometry.width()
    screen_height = screen_geometry.height()

    # Tạo cửa sổ ứng dụng
    window = CombinedApp()
    
    # Cài đặt kích thước cửa sổ theo kích thước màn hình
    window.resize(screen_width, screen_height)
    window.show()

    sys.exit(app.exec())

