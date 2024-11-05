from confluent_kafka import Producer
import json
import time
import random

# Konfigurasi Kafka Producer
producer = Producer({'bootstrap.servers': 'localhost:9092'})

# Fungsi untuk mengirim data suhu dari 3 sensor
def send_temperature_data():
    sensors = ['S1', 'S2', 'S3']
    while True:
        for sensor_id in sensors:
            data = {
                'sensor_id': sensor_id,
                'temperature': random.randint(60, 100)  # suhu acak antara 60-100°C
            }
            producer.produce('sensor-suhu', key=sensor_id, value=json.dumps(data))
            print(f"Data sent: {data}")
            producer.flush()  # memastikan data terkirim
        time.sleep(1)

try:
    send_temperature_data()
except KeyboardInterrupt:
    producer.flush()
