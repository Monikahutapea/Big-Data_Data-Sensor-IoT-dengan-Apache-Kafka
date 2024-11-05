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

# Cross join filtered data with high temperature info to add Keterangan
enriched_data = filtered_data.crossJoin(high_temp_info)

# Display results to console with additional processing information
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