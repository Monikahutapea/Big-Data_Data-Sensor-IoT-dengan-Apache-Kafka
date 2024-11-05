## Big Data(B)_Data Sensor IoT dengan Apache Kafka


| Nama                   | NRP        |
|------------------------|------------|
| Monika Damelia Hutapea | 5027221011 |
| Angella Christie       | 5027221047 |

### A. Latar Belakang Masalah
Sebuah pabrik memiliki beberapa mesin yang dilengkapi sensor suhu. Data suhu dari setiap mesin perlu dipantau secara real-time untuk menghindari overheating. Setiap sensor akan mengirimkan data suhu setiap detik, dan pabrik membutuhkan sistem yang dapat mengumpulkan, menyimpan, dan menganalisis data suhu ini.

### B. Studi Kasus Insiden Sederhana
Pabrik membutuhkan aliran data sensor yang dapat diteruskan ke layanan analitik atau dashboard secara langsung. Apache Kafka akan digunakan untuk menerima dan mengalirkan data suhu, sementara PySpark akan digunakan untuk mengolah dan memfilter data tersebut.

### C. Langkah Pengerjaan
#### 1. Lakukan instalasi yang dibutuhkan, seperti pyspark, python, confluent-kafka

![Screenshot (90)](https://github.com/user-attachments/assets/1ea0b675-1dc8-4137-8ea7-d93449eb1f34)

![Screenshot (91)](https://github.com/user-attachments/assets/7162f3bd-94c5-4f35-971c-d76941aed93d)

![image](https://github.com/user-attachments/assets/1ca893c6-ec00-4830-97ed-fc74613eb41d)

#### 2. Buat topik kafka untuk data suhu
Di Apache Kafka buat topik bernama "sensor-suhu" yang akan menerima data suhu dari sensor mesin dengan menggunakan command `docker exec -it kafka kafka-topics.sh --create --topic sensor-suhu --bootstrap-server localhost:9092 --replication-factor -partitions 1`. Dengan perintah ini, topik Kafka bernama "sensor-suhu" dibuat dengan satu partisi dan satu replika pada server Kafka yang berjalan di localhost:9092.

![Screenshot 2024-11-04 135214](https://github.com/user-attachments/assets/1d5d86f2-346d-475a-aef0-aa7840c9fcbc)


#### 3. Buat file yaitu consumer.py, producer.py, docker-compose.yml kemudian dijalankan

**File**

- docker-compose.yml

```
services:
  zookeeper:
    image: 'bitnami/zookeeper:latest'
    container_name: zookeeper
    environment:
      - ALLOW_ANONYMOUS_LOGIN=yes
    ports:
      - '2181:2181'


  kafka:
    image: 'bitnami/kafka:latest'
    container_name: kafka
    environment:
      - KAFKA_BROKER_ID=1
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
      - ALLOW_PLAINTEXT_LISTENER=yes
      - KAFKA_LISTENERS=PLAINTEXT://:9092
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092
    ports:
      - '9092:9092'
    depends_on:
      - zookeeper
```

**Keterangan:**
File docker-compose.yml ini mengatur untuk menjalankan Apache Kafka dan Zookeeper secara otomatis melalui Docker. Zookeeper digunakan sebagai layanan koordinasi Kafka dan berjalan di port default 2181, dengan akses tanpa autentikasi diaktifkan. Kafka sendiri dikonfigurasi untuk mendengarkan pada port 9092 dengan komunikasi plaintext dan dihubungkan ke Zookeeper melalui KAFKA_ZOOKEEPER_CONNECT. Pengaturan depends_on memastikan Kafka hanya berjalan setelah Zookeeper siap, sehingga mempermudah konfigurasi Kafka dan Zookeeper tanpa instalasi manual di mesin lokal.

- consumer.py

```
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType


# Create a Spark session with Kafka connector
spark = SparkSession.builder \
    .appName("Sensor Temperature Consumer") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.0.1") \
    .getOrCreate()


# Read data from Kafka
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "sensor-suhu") \
    .option("startingOffsets", "latest") \
    .load()


# Define schema for the data
schema = StructType([
    StructField("sensor_id", StringType(), True),
    StructField("temperature", IntegerType(), True)
])


# Convert the Kafka value into a DataFrame
sensor_data = df.selectExpr("CAST(value AS STRING)").select(F.from_json(F.col("value"), schema).alias("data"))


# Extract sensor_id and temperature from the data structure
sensor_data = sensor_data.select("data.sensor_id", "data.temperature")


# Filter temperatures above 80°C
filtered_data = sensor_data.filter(sensor_data.temperature > 80)


# Create a DataFrame for additional information about high temperature
high_temp_info = spark.createDataFrame(
    [("Suhu terlalu tinggi",)],
    ["Keterangan"]
)
enriched_data = filtered_data.crossJoin(high_temp_info)


query = enriched_data.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", "false") \
    .start()


# Handle errors and await termination
try:
    query.awaitTermination()
except KeyboardInterrupt:
    print("Streaming stopped by user.")
finally:
    spark.stop()
```

**Keterangan:**
Kode diatas berfungsi sebagai consumer untuk data suhu sensor yang disalurkan melalui Apache Kafka. Kode ini membuat SparkSession yang mendukung koneksi ke Kafka, memungkinkan PySpark untuk membaca stream data dari topik "sensor-suhu" di Kafka. Data yang diterima diubah ke bentuk JSON dan dipetakan ke skema yang terdiri dari dua kolom, yaitu sensor_id dan temperature. Kode ini kemudian menyaring suhu di atas 80°C sebagai indikator potensi overheating. Untuk data yang memenuhi syarat ini, aplikasi menambahkan kolom informasi tambahan dengan pesan peringatan "Suhu terlalu tinggi" menggunakan cross join. Hasilnya ditampilkan langsung di console, menandakan suhu berbahaya secara real-time.

- producer.py

```
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
```

- Keterangan:
Kode di atas adalah producer kafka yang mensimulasikan data suhu dari tiga sensor mesin (dengan ID S1, S2, dan S3). Kode ini menggunakan pustaka confluent_kafka untuk mengkonfigurasi producer kafka agar terhubung ke broker Kafka pada localhost:9092. Dalam fungsi send_temperature_data, loop tak terbatas menghasilkan data suhu acak antara 60°C hingga 100°C untuk setiap sensor. Data ini dikemas dalam format JSON yang berisi sensor_id dan temperature, lalu dikirim ke topik Kafka bernama "sensor-suhu". Setiap data yang berhasil dikirim ditampilkan di console sebagai log untuk pemantauan. Producer.flush() digunakan untuk memastikan semua pesan dikirim sebelum melanjutkan ke iterasi berikutnya. Jika proses dihentikan (misalnya dengan keyboard interrupt), producer akan melakukan flush terakhir untuk memastikan semua pesan tertunda dikirim sebelum program berhenti.

**Jalankan code**

![image](https://github.com/user-attachments/assets/441d0490-3759-4f66-af80-5a40e89a73f9)

![Screenshot (89)](https://github.com/user-attachments/assets/5be0d813-f709-4b07-94b7-19eed02b8adc)

![image](https://github.com/user-attachments/assets/34eb333a-6007-4d9c-bd4f-789826fe2843)

![Screenshot (93)](https://github.com/user-attachments/assets/47d46bb4-71a9-4687-a901-501d2f7af477)

![Screenshot (94)](https://github.com/user-attachments/assets/7f1988a9-b132-4ccd-bc5e-a8f2bc8a6230)

**Output yang dihasilkan**

![Screenshot (95)](https://github.com/user-attachments/assets/61763308-134f-4c64-b19d-247548886e03)

![Screenshot (96)](https://github.com/user-attachments/assets/dcc544d4-560f-41cc-87c9-ed8aa1eae0e6)

![Screenshot (97)](https://github.com/user-attachments/assets/48032910-27b2-404d-9a29-827ad0bb93f2)

![Screenshot (98)](https://github.com/user-attachments/assets/9947086d-3497-4a87-8b73-4a13882191f8)



