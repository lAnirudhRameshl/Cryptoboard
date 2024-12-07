import json
import subprocess
import time
from urllib3 import PoolManager
from urllib.parse import urlencode
from kafka import KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError
import kafka

# KAFKA_PATH = "kafka_2.13-3.9.0/bin/kafka-server-start.sh"
# CONFIG_PATH = "kafka_2.13-3.9.0/config/server.properties"
# ZOOKEEPER_PATH = "kafka_2.13-3.9.0/bin/zookeeper-server-start.sh"
# ZOOKEEPER_CONFIG = "kafka_2.13-3.9.0/config/zookeeper.properties"
BOOTSTRAP_SERVERS = ["kafka:9092"]


# def startKafka():
#     print("Starting Zookeeper server...")
#     try:
#         zookeeper = subprocess.Popen(
#             [ZOOKEEPER_PATH, ZOOKEEPER_CONFIG],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE
#         )
#         time.sleep(10)  # Wait for Zookeeper to start
#         print("...Zookeeper server started")
#     except Exception as e:
#         print(f"Error starting Zookeeper server: {e}")
#         exit(1)

#     print("Starting Kafka server...")
#     try:
#         kafka = subprocess.Popen(
#             [KAFKA_PATH, CONFIG_PATH],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE
#         )
#         time.sleep(10)  # Wait for Kafka to start
#         print("...Kafka server started")
#         return kafka
#     except Exception as e:
#         print(f"Error starting Kafka server: {e}")
#         exit(1)


def createKafkaProducer():
    print("Creating Kafka producer...")
    retries = 3
    while retries > 0:
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                api_version=(0, 10, 1),
                retry_backoff_ms=1000,
                request_timeout_ms=30000
            )
            print("...Kafka producer created")
            return producer
        except Exception as e:
            print(f"Error creating Kafka producer: {e}")
            retries -= 1
            time.sleep(5)
    print("Failed to create Kafka producer")
    exit(1)


# def createKafkaTopics(sources):
#     admin_client = KafkaAdminClient(bootstrap_servers='localhost:9092')
#     topics = []
#     for s in sources:
#         topics.append(NewTopic(name=s["name"], num_partitions=1, replication_factor=1))

#     try:
#         admin_client.create_topics(new_topics=topics, validate_only=False)
#         print("Topics created")
#     except TopicAlreadyExistsError:
#         print("Topics already exist, moving on")
#     except Exception as e:
#         print(f"Error creating topics: {e}")
#         exit(1)


def main():
    # Read configuration files
    try:
        sources = json.loads(open("sources.json", "r").read())
        currencies = json.loads(open("currencies.json", "r").read())
    except Exception as e:
        print(f"Error reading configuration files: {e}")
        exit(1)

    # Start Kafka infrastructure
    # kafka = startKafka()
    # createKafkaTopics(sources)
    producer = createKafkaProducer()

    # List created topics
    # result = subprocess.run(
    #     [KAFKA_PATH, "--list", "--bootstrap-server", "localhost:9092"],
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.PIPE,
    #     text=True
    # )
    # print("Available topics:", result.stdout)

    # now run poller.py
    # subprocess.run(["python", "poller.py"])


    # Initialize HTTP client
    http = PoolManager()

    # Process each source and currency
    try:
        for source in sources:
            print(f"Processing source: {source['name']}")
            for currency in currencies["cryptocurrencies"]:
                print(f"Processing currency: {currency['name']}")
                base_url = source["url"]
                params = {"q": currency["name"]}
                fullURL = base_url + "&" + urlencode(params)

                try:
                    response = http.request("GET", fullURL)
                    data = json.loads(response.data.decode('utf-8'))
                    data['currency'] = currency['id']
                    producer.send(source["name"], value=data)
                    producer.flush()  # Ensure message is sent
                    print(f"Published {currency['name']} data to {source['name']} topic")
                except Exception as e:
                    print(f"Error processing {currency['name']} from {source['name']}: {e}")
                    continue  # Skip to next currency instead of exiting

                time.sleep(1)  # Rate limiting
    finally:
        producer.close()
        # kafka.terminate()


if __name__ == "__main__":
    while True:
        main()
        print("Waiting to crawl after 12 hours....")
        time.sleep(43200)
