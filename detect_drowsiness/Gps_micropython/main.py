###### IMPORT LIB ######
from umqtt.simple import MQTTClient # import MQTTClient class
import network
import time
from machine import Pin, UART
import ssl
from micropyGPS import MicropyGPS
import gc
import machine
 
gc.collect()
######  INIIT COMPONENT / PIN
led = Pin(19, Pin.OUT)
buzzer = Pin(22, Pin.OUT)
button = Pin(23, Pin.IN)
button.value(0)

###### GPS ######
my_gps = MicropyGPS()
gps_serial = UART(2, baudrate = 9600, tx = 17, rx = 16)

def tracker():
    global Latitude, Longitude, Speed
    Latitude = my_gps.latitude_string()
    Longitude = my_gps.longitude_string()
    Speed = my_gps.speed_string()
    try:
        while gps_serial.any():
            data = gps_serial.read()
            for byte in data:
                stat = my_gps.update(chr(byte))
                # if stat is not None:
                    # Print parsed GPS data
                    # print('UTC Timestamp:', my_gps.timestamp)
                    # print('Date:', my_gps.date_string('long'))
                    # print('Latitude:', Latitude)
                    # print('Longitude:', Longitude)
                    # print('Speed:', Speed)
                    # print('Altitude:', my_gps.altitude)
                    # print('Satellites in use:', my_gps.satellites_in_use)
                    # print('Horizontal Dilution of Precision:', my_gps.hdop)
                    # print()    
    except Exception as e:
        print(f"An error occurred: {e}")
    return Latitude, Longitude, Speed

###### Wifi #######
WIFI_SSID = "Abc"
WIFI_PASSWORD = "12345678"
def blink_led():
    led.value(1)
    time.sleep_ms(50)
    led.value(0)
    time.sleep_ms(50)
    return
def ConnectWifi(wifi_ssid, wifi_password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(wifi_ssid, wifi_password)
    print("Connecting to wifi...")
    while not wlan.isconnected():
        blink_led()
        print(".")
        time.sleep(1)
    print("Connected to the Wifi")

###### MQTT #####
MQTT_BROKER_URL ="b8fe3c14237c4aefb0823289870c4d8b.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_CLIENT_ID = "ESP32"
MQTT_USER = "VuUwU"
MQTT_PW = "VuUwU@123"
MQTT_KEEP_ALIVE = 360
MQTT_CLEAN_SESSION = True
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.verify_mode = ssl.CERT_NONE

# umqtt.simple as MQTT
# (self, client_id, server, port, user, password, keepalive, ssl)
def mqtt_connect():
    global mqtt_client
    print("Connecting to MQTT")
    try:
        print(".")
        mqtt_client = MQTTClient(client_id=MQTT_CLIENT_ID, server=MQTT_BROKER_URL, port=MQTT_PORT,
                                 user=MQTT_USER, password=MQTT_PW, ssl=context)
        mqtt_client.connect(MQTT_CLEAN_SESSION)
    except Exception as e:
        if e == "-202":
            print(f"OSError: {e}")
            print(f"Try connect to wifi")
    print("Connected to HiveMQ Broker")
    return mqtt_client

## Subcribe Topic
Topic = b"#"
led_state = 0
buzzer_state = 0
def sub_cb(topic, msg):
    global led_state, buzzer_state, mqtt_client
    print(f"Recieved msgs: {(topic, msg)}")
    if topic == b"buzzer":
        if msg == b"on":
            buzzer.value(1)
            buzzer_state = 1
            print(f"Location: {Latitude}, {Longitude}, Speed: {Speed}")
            mqtt_client.publish(b"Location", f"{Latitude}, {Longitude}")
            time.sleep_ms(10)
            mqtt_client.publish(b"Speed", Speed)
            time.sleep_ms(10)
            gc.collect()
        elif msg == b"pressed":
            gc.collect()
            buzzer.value(0)
            gc.collect()
            buzzer_state = 0
    return

def main():
    global mqtt_client
#    try:
    ConnectWifi(WIFI_SSID,WIFI_PASSWORD)
    gc.collect()
    mqtt_connect()
    gc.collect()
    mqtt_client.set_callback(sub_cb)
    print("I was here")
#    mqtt_client.connect()
    gc.collect()
    try:
        mqtt_client.subscribe(Topic)
    except Exception as e:
        print(f"OSError:{e}")
    led.value(1)
    print("Connected to %s, subscribed to %s topic" % (MQTT_BROKER_URL, Topic))
#    except Exception as e:
#        print(f"It stops here Error: {e}")
#        gc.collect()
#        machine.reset()
    try:
        while 1:
            tracker()
            mqtt_client.check_msg()
            if button.value() == 1:
                if buzzer_state == 1:
                    print("Button pressed")
                    mqtt_client.publish(b"buzzer",b"pressed")
            time.sleep_ms(200)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        mqtt_client.disconnect()
        print("Disconnected")

main()