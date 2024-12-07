import json
from concurrent.futures import ThreadPoolExecutor
from kafka import KafkaConsumer
import handlers
import signal
import sys


def deserialize(message_bytes):
    try:
        if message_bytes is None:
            print("Received None message")
            return None

        decoded = message_bytes.decode('utf-8')
        print("Raw message: " + decoded)

        if not decoded.strip():
            print("Received empty message")
            return None

        return json.loads(decoded)
    except UnicodeDecodeError as e:
        print("Failed to decode message bytes" + str(e))
        return None
    except json.JSONDecodeError as e:
        print("Failed to parse JSON")
        return None
    except Exception as e:
        print("Error during deserialization: " + str(e))
        return None


class KafkaPoller:
    def __init__(self, bootstrap_servers, topics, group_id, message_handlers, max_workers, poll_interval,
                 auto_offset_reset):
        self.processing_futures = set()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.consumer = None
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.group_id = group_id
        self.message_handlers = message_handlers
        self.poll_interval = poll_interval
        self.auto_offset_reset = auto_offset_reset
        self.running = True

    def create_consumer(self):
        try:
            self.consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                enable_auto_commit=False,
                value_deserializer=lambda x: deserialize(x),
                auto_offset_reset=self.auto_offset_reset
            )
            print("Connected to Kafka, subscribed to topics: " + str(self.topics))
        except Exception as e:
            print("Error connecting to Kafka: " + str(e))
            sys.exit(1)

    def handle_message(self, message):
        try:
            if message.value is None:
                print("Skipping message with None value from topic " + message.topic)
                return

            source = message.topic
            print("Processing message from topic " + source + ": " + str(message.value))
            handler = self.message_handlers.get_handler(source)
            if handler is not None:
                handler.handle(message.value)
                self.consumer.commit()
            else:
                print("No handler found for source: " + source)
        except Exception as e:
            print("Error handling message: " + str(e))

    def start(self):
        print("Starting Kafka poller...")
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        self.create_consumer()

        flag = False

        try:
            while self.running:
                messages = self.consumer.poll(timeout_ms=int(self.poll_interval * 1000))
                if not messages:
                    if not flag:
                        handlers.calculator.calculate_metrics(24)
                        flag = True
                    continue

                print("Received message batch: " + str(len(messages)) + " partition(s)")

                for tp, msgs in messages.items():
                    print("Processing " + str(len(msgs)) + " messages from " + tp.topic + ":" + str(tp.partition))
                    for message in msgs:
                        future = self.executor.submit(self.handle_message, message)
                        self.processing_futures.add(future)
                        future.add_done_callback(lambda x: self.processing_futures.remove(x))
                    flag = False
        except Exception as e:
            print("Error in poller loop: " + str(e))
        finally:
            self.shutdown(None, None)

    def shutdown(self, signum, frame):
        print("Shutting down gracefully...")
        self.running = False
        self.executor.shutdown(wait=True)
        if self.consumer:
            self.consumer.close()
        sys.exit(0)


def main():
    try:
        # Read sources
        with open("sources.json", "r") as f:
            sources = json.load(f)

        topics = [source['name'] for source in sources]
        message_handlers = handlers.factory

        poller = KafkaPoller(
            bootstrap_servers="kafka:9092",
            topics=topics,
            group_id="my-consumer-group",
            message_handlers=message_handlers,
            max_workers=5,
            poll_interval=1.0,
            auto_offset_reset='earliest'
        )
        poller.start()
    except Exception as e:
        print(f"Error starting poller: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
