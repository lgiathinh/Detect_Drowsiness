from PySide6 import QtCore, QtWidgets, QtGui 
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QTableWidgetItem
import cv2  
import numpy as np  
import serial.tools.list_ports
import dlib  
from imutils import face_utils  
from scipy.spatial import distance  
import rpc 
from datetime import datetime
import paho.mqtt.client as mqtt
import setting
import time

setting.init()
print(setting.M)
## Define ##
MQTT_BROKER_URL ="b8fe3c14237c4aefb0823289870c4d8b.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_CLIENT_ID = "COMPUTER"
MQTT_USER = "VuUwU"
MQTT_PW = "VuUwU@123"
MQTT_CLEAN_SESSION = True
MQTT_KEEP_ALIVE = 360
MQTT_VER = 3

# buzzer_flags = 0
lat_deg = setting.lat_deg
lat_min = setting.lat_min
lat_dir = setting.lat_dir
long_deg = setting.long_deg
long_min = setting.long_min
long_dir = setting.long_dir
## MQTT ##
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,MQTT_CLIENT_ID, clean_session=MQTT_CLEAN_SESSION, protocol=MQTT_VER)
client.username_pw_set(MQTT_USER, MQTT_PW)
client.tls_set()  # Uses default SSL/TLS settings 

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("Connected successfully to MQTT")
    else:
        print(f"Failed to connect, reason code {reason_code}")

def on_subscribe(mqttc, obj, mid, reason_code_list, properties):
    print("Subscribed: " + str(mid) + " " + str(reason_code_list))

def on_message(client, userdata, message):
    print(f"Messgae received: Topic'{message.topic}' and msg:'{str(message.payload.decode().strip().lower())}'")
    if message.topic == "buzzer" and message.payload.decode().strip().lower() == "pressed":
        buzzer_flags = 0
    if message.topic == "Location":
        Location = {message.payload.decode()}
        print(f"Location: {Location}")
        lat_deg = parsing_location(Location)[0]
        lat_min = parsing_location(Location)[1]
        lat_dir = parsing_location(Location)[2]
        long_deg = parsing_location(Location)[3]
        long_min = parsing_location(Location)[4]
        long_dir = parsing_location(Location)[5]
        print("Latitude Degrees:", lat_deg)
        print("Latitude Minutes:", lat_min)
        print("Latitude Direction:", lat_dir)
        print("Longitude Degrees:", long_deg)
        print("Longitude Minutes:", long_min)
        print("Longitude Direction:", long_dir)
        setting.lat_deg = lat_deg
        setting.lat_min = lat_min
        setting.lat_dir = lat_dir
        setting.long_deg = long_deg
        setting.long_min = long_min
        setting.long_dir = long_dir
        setting.new_location = 1
        print("Done transfer to global variables")
        setting.M.add_location(lat_deg, lat_min, lat_dir, long_deg, long_min, long_dir)
    if message.topic == "Speed":
        speed = message.payload.decode().strip()
        setting.speed = speed
        print(f"Speed: {speed}")   
        
def parsing_location(Location):
    data_string = list(Location)[0]
    parts = [part.strip() for part in data_string.split(',')]
    lat_deg = parts[0]
    lat_min, lat_dir = parts[1].split("' ")
    long_deg = parts[2]
    long_min, long_dir = parts[3].split("' ") 
    lat_deg = int(lat_deg)
    lat_min = float(lat_min)
    long_deg = int(long_deg)
    long_min = float(long_min)
    lat_dir = f"'{lat_dir}'"
    long_dir = f"'{long_dir}'"
    return lat_deg, lat_min, lat_dir, long_deg, long_min, long_dir

client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe
client.connect(MQTT_BROKER_URL, MQTT_PORT, keepalive=MQTT_KEEP_ALIVE)
client.subscribe("#",0)
client.loop_start()

def send_msg(topic, msg):
    client.publish(topic,msg)
    print(f"Have published {topic}: {msg}")

# Hằng số cho việc phát hiện buồn ngủ
thresh = 0.25  # Ngưỡng cho tỷ lệ mắt mở
frame_check = 60  # Số khung hình kiểm tra drowsiness


detector = dlib.get_frontal_face_detector()
predict = dlib.shape_predictor("models/shape_predictor_68_face_landmarks.dat")

# Định nghĩa lớp ImgLabel kế thừa QLabel để nhận sự kiện nhấn chuột
class ImgLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal() 

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        self.status = 'CLICKED'  
        self.pos_1st = ev.position() 
        self.clicked.emit()  
        return super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.status = 'RELEASED' 
        self.pos_2nd = ev.position()  
        self.clicked.emit() 
        return super().mouseReleaseEvent(ev)

class EspCamWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.rpc_master = None
        self.capture_timer = None
        self.drowsy_counter = 0  
        self.drowsy_count = 0  
        self.yawn_count = 0  
        self.yawning = False  
        self.latitude = "NaN"  
        self.longitude = "NaN"
        self.speed = "N/A"

        # Cập nhật thời gian mỗi giây
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # 1000ms = 1 giây
        
        
         # Tạo bảng với hai cột có độ rộng bằng nhau
        self.drowsy_log_table = QtWidgets.QTableWidget(0, 4)
        self.drowsy_log_table.setHorizontalHeaderLabels(["Thời gian", "Trạng thái", "Vị Trí", "Tốc độ"])
        header = self.drowsy_log_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)  # Đặt độ rộng cột bằng nhau
        self.drowsy_log_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.drowsy_log_table.setFixedHeight(200)
        
        self.populate_ui()  # Tạo giao diện người dùng
    
    def update_speed(self, speed):
        self.speed_label.setText(f"Tốc độ: {setting.speed}")

        
    def log_drowsy_event(self):
        print("New log")
        current_time = QDateTime.currentDateTime().toString("HH:mm:ss")
        self.latitude = f"{setting.lat_deg}, {setting.lat_min}, {setting.lat_dir}" 
        self.longitude = f"{setting.long_deg}, {setting.long_min}, {setting.long_dir}"
        location_info = f"Vĩ độ: {self.latitude}, Kinh độ: {self.longitude}"
        self.speed = setting.speed
        speed_info = f"{self.speed}"

        row_position = self.drowsy_log_table.rowCount()
        self.drowsy_log_table.insertRow(row_position)
        
        # Cập nhật nội dung các cột
        self.drowsy_log_table.setItem(row_position, 0, QTableWidgetItem(current_time))
        self.drowsy_log_table.setItem(row_position, 1, QTableWidgetItem("Tài xế ngủ gật"))
        self.drowsy_log_table.setItem(row_position, 2, QTableWidgetItem(location_info))
        self.drowsy_log_table.setItem(row_position, 3, QTableWidgetItem(speed_info))
        
        # Bật tính năng word wrap
        self.drowsy_log_table.setWordWrap(True)
        
        # Điều chỉnh chiều cao hàng để vừa nội dung
        self.drowsy_log_table.resizeRowsToContents()

        
    def update_time(self):
        """Hàm cập nhật thời gian hiện tại lên nhãn thời gian"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(f"Time: {current_time}")

        
    def populate_ui(self):
        # Tạo layout chính cho ứng dụng
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.populate_ui_image()  # Tạo giao diện cho phần hiển thị hình ảnh
        self.populate_ui_ctrl()  # Tạo giao diện cho phần điều khiển
        self.main_layout.addLayout(self.image_layout)
        self.main_layout.addLayout(self.ctrl_layout)
        
        self.drowsy_count_label = QtWidgets.QLabel("Drowsy Count: 0")
        self.drowsy_count_label.setFixedHeight(40) 

        self.drowsy_alert_label = QtWidgets.QLabel("")
        self.drowsy_count_label.setStyleSheet("""
            QLabel {
                background-color: white;      /* Màu nền cam */
                color: black;                  /* Màu chữ đen */
                border: 2px solid black;       /* Đường viền đen */
                border-radius: 5px;            /* Góc bo tròn */
                padding: 5px;                  /* Khoảng cách giữa nội dung và viền */
                font-size: 14px;               /* Kích thước chữ */
                font-weight: bold;             /* Chữ đậm */
            }
        """)
        self.ctrl_layout.addRow(self.drowsy_count_label)
        
         # Thêm nhãn hiển thị số lần ngáp
        self.yawn_count_label = QtWidgets.QLabel("Yawn Count: 0")
        self.yawn_count_label.setFixedHeight(40)  # Đặt chiều rộng cố định
        self.yawn_alert_label = QtWidgets.QLabel("")
        self.yawn_count_label.setStyleSheet("""
            QLabel {
                background-color: white;      /* Màu nền cam */
                color: black;                  /* Màu chữ đen */
                border: 2px solid black;       /* Đường viền đen */
                border-radius: 5px;            /* Góc bo tròn */
                padding: 5px;                  /* Khoảng cách giữa nội dung và viền */
                font-size: 14px;               /* Kích thước chữ */
                font-weight: bold;             /* Chữ đậm */
            }
        """)
        self.ctrl_layout.addRow(self.yawn_count_label)
        
        # Nhãn hiển thị thời gian hiện tại
        self.time_label = QtWidgets.QLabel("Time: --:--:--")
        self.time_label.setFixedHeight(40)  # Đặt chiều rộng cố định
        self.time_label.setStyleSheet("""
            QLabel {
                background-color: white;      /* Màu nền cam */
                color: black;                  /* Màu chữ đen */
                border: 2px solid black;       /* Đường viền đen */
                border-radius: 5px;            /* Góc bo tròn */
                padding: 5px;                  /* Khoảng cách giữa nội dung và viền */
                font-size: 14px;               /* Kích thước chữ */
                font-weight: bold;             /* Chữ đậm */
            }
        """)
        self.ctrl_layout.addRow(self.time_label)
        
        # Định dạng bảng cho đẹp
        self.drowsy_log_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                font-size: 14px;
            }
            QHeaderView::section {
                background-color: #A6AEBF;
                font-weight: bold;
            }
        """)
        # Thêm bảng vào layout điều khiển (hoặc vị trí khác tùy thuộc vào bố cục của bạn)
        self.ctrl_layout.addRow(self.drowsy_log_table)
    
    def update_drowsy_alert(self):
        # Lấy thời gian hiện tại
        current_time = datetime.now().strftime("%H:%M:%S")

        # Tạo thông báo với kinh độ và vĩ độ
        alert_message = (
            f"Tài xế ngủ gật lúc {current_time}\n"
            f"Vĩ độ: {self.latitude}\n"
            f"Kinh độ: {self.longitude}"
        )

        # Hiển thị thông báo
        self.drowsy_alert_label.setText(alert_message)
        self.drowsy_alert_label.update()  # Cập nhật giao diện ngay lập tức

    
    def update_drowsy_count(self):
        self.drowsy_count += 1  # Tăng số lần phát hiện buồn ngủ
        self.drowsy_count_label.setText(f"Drowsy Count: {self.drowsy_count}")  # Cập nhật giao diện
    
    def update_yawn_alert(self):
        # Lấy thời gian hiện tại và hiển thị thông báo
        current_time = datetime.now().strftime("%H:%M:%S")
        self.yawn_alert_label.setText(f"Tài xế buồn ngủ lúc {current_time}")
        self.yawn_alert_label.update()  # Cập nhật giao diện ngay lập tức
    
    def update_yawn_count(self):
        # Cập nhật số lần ngáp trên giao diện
        self.yawn_count += 1
        self.yawn_count_label.setText(f"Yawn Count: {self.yawn_count}")
       
    def populate_ui_image(self):
        # Tạo giao diện cho phần hình ảnh
        self.image_layout = QtWidgets.QVBoxLayout()
        self.image_layout.setAlignment(QtCore.Qt.AlignTop)
        self.preview_img = QtWidgets.QLabel("Preview Image")
        self.preview_img.resize(320, 240)
        self.image_layout.addWidget(self.preview_img)
        

    def populate_ui_ctrl(self):
        # Tạo giao diện cho phần điều khiển
        self.ctrl_layout = QtWidgets.QFormLayout() 
        self.ctrl_layout.setAlignment(QtCore.Qt.AlignTop)

        # Tạo danh sách các cổng ESP32 có sẵn
        self.esp32_port = QtWidgets.QComboBox()
        self.esp32_port.addItems([port for (port, desc, hwid) in serial.tools.list_ports.comports()])
        self.ctrl_layout.addRow("ESP32 Port", self.esp32_port)

        # Nút kết nối ESP32
        self.esp32_button = QtWidgets.QPushButton("Connect")
        self.esp32_button.clicked.connect(self.connect_esp32)
        self.ctrl_layout.addRow(self.esp32_button)

    def connect_esp32(self):
        global connect
        # Kết nối đến ESP32 qua cổng được chọn
        port = self.esp32_port.currentText()
        connect = 1
        try:
            print(connect)
            self.rpc_master = rpc.rpc_usb_vcp_master(port)
            self.esp32_button.setText("Connected")
            self.esp32_button.setEnabled(False)
            self.capture_photo()
            if connect == 1:
                self.start_capture_timer()  # Bắt đầu chụp ảnh sau khi kết nối
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def start_capture_timer(self):
        # Khởi tạo bộ đếm thời gian để chụp ảnh mỗi giây
        self.capture_timer = QtCore.QTimer(self)
        self.capture_timer.timeout.connect(self.capture_photo)
        self.capture_timer.start(100)
        
    def capture_photo(self):
        global connect
        if self.rpc_master is None:
            return
        try:
            result = self.rpc_master.call("jpeg_image_snapshot", recv_timeout=1000)
            if result is not None:
                jpg_sz = int.from_bytes(result.tobytes(), "little")
                buf = bytearray(b'\x00' * jpg_sz)
                result = self.rpc_master.call("jpeg_image_read", recv_timeout=1000)
                self.rpc_master.get_bytes(buf, jpg_sz)
                img = cv2.imdecode(np.frombuffer(buf, dtype=np.uint8), cv2.IMREAD_COLOR)
                
                # Phát hiện trạng thái buồn ngủ/ngáp
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                subjects = detector(gray, 0)
                for subject in subjects:
                    shape = predict(gray, subject)
                    shape = face_utils.shape_to_np(shape)
                    
                    if self.detect_yawn(shape):
                        print("Yawn detected")

                    drowsy = self.detect_drowsiness(img)
                    if drowsy:
                        self.drowsy_counter += 1
                        if self.drowsy_counter >= 3:
                            send_msg("buzzer","on")
                            time.sleep(1)
                            self.buzzer_flags = 1
                            self.drowsy_counter = 0
                            self.update_drowsy_alert()
                            self.update_drowsy_count()
                            try: 
                                if setting.new_location!=0:
                                    self.log_drowsy_event()
                            except:
                                continue
                            self.drowsy_counter = 0
                    else:
                        self.drowsy_counter = 0
                # Cập nhật hình ảnh hiển thị
                self.update_image(img.copy())
                connect = 1
            else:
                QtWidgets.QMessageBox.warning(self, "Warning", "Failed to capture photo.")
                self.esp32_button.setEnabled(True)
                self.esp32_button.setText("Connect")
                connect = 0
                return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))


    def detect_drowsiness(self, img):
        # Chuyển đổi ảnh sang màu xám và phát hiện khuôn mặt
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        subjects = detector(gray, 0)
        for subject in subjects:
            shape = predict(gray, subject)  # Xác định các điểm trên khuôn mặt
            shape = face_utils.shape_to_np(shape)
            left_eye = shape[42:48]
            right_eye = shape[36:42]
            left_ear = self.eye_aspect_ratio(left_eye)
            right_ear = self.eye_aspect_ratio(right_eye)
            ear = (left_ear + right_ear) / 2.0
            if ear < thresh:
                return True
        return False

    def detect_yawn(self, shape):
        top_lip = shape[50:53]
        top_lip = np.concatenate((top_lip, shape[61:64]))
        low_lip = shape[56:59]
        low_lip = np.concatenate((low_lip, shape[65:68]))
        
        top_mean = np.mean(top_lip, axis=0)
        low_mean = np.mean(low_lip, axis=0)
        
        lip_distance = distance.euclidean(top_mean, low_mean)
        yawn_thresh = 12  # Ngưỡng để phát hiện ngáp, có thể điều chỉnh

        if lip_distance > yawn_thresh:
            # Nếu miệng đang mở và trạng thái hiện tại là không ngáp, đánh dấu là bắt đầu ngáp
            if not self.yawning:
                self.yawning = True
        else:
            # Nếu miệng đóng lại sau khi mở, đếm 1 lần ngáp và đặt trạng thái ngáp lại là False
            if self.yawning:
                self.yawning = False
                self.update_yawn_count()  # Cập nhật số lần ngáp
                return True  # Phát hiện một lần ngáp hoàn chỉnh

        return False  


    def eye_aspect_ratio(self, eye):
        # Tính tỷ lệ mắt để xác định trạng thái mở hoặc nhắm mắt
        A = distance.euclidean(eye[1], eye[5])
        B = distance.euclidean(eye[2], eye[4])
        C = distance.euclidean(eye[0], eye[3])
        ear = (A + B) / (2.0 * C)
        return ear

    def update_image(self, img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, c = img.shape
        img = QtGui.QImage(img.data, w, h, QtGui.QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        self.preview_img.setPixmap(pixmap.scaled(320, 240, QtCore.Qt.KeepAspectRatio))

    def closeEvent(self, event):
        if self.rpc_master is not None:
            self.rpc_master.close()
            
