#!/usr/bin/env python3
"""
=============================================================================
Enterprise Data Lakehouse Platform - Real-Time Kafka Event Producer (M02)
=============================================================================
Simulates real-time retail / POS event streams producing JSON transactions
into Kafka/Redpanda topic 'enterprise.orders.events'.

Features:
- Configurable event generation rate (events/sec) and volume.
- Automatic fallback simulation when Kafka broker is unreachable or in dry-run mode.
- Structured performance metrics (events/sec, latency, total throughput).
"""

import os
import sys
import json
import time
import random
import logging
import argparse
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [StreamProducer] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("KafkaStreamProducer")

# Check for Kafka library availability
try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    try:
        from kafka.producer import KafkaProducer
        KAFKA_AVAILABLE = True
    except ImportError:
        KAFKA_AVAILABLE = False


def generate_event(order_id: int) -> dict:
    """Generate a single realistic transaction event payload."""
    unit_price = round(random.uniform(50.0, 3500.0), 2)
    quantity = round(random.uniform(1.0, 10.0), 2)
    discount = round(random.uniform(0.0, 100.0), 2) if random.random() > 0.6 else 0.0

    statuses = ["COMPLETED", "COMPLETED", "COMPLETED", "PENDING", "CANCELLED"]
    status = random.choice(statuses)

    return {
        "order_id": order_id,
        "customer_id": random.randint(1, 500),
        "order_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "branch_id": random.randint(1, 20),
        "product_id": random.randint(1, 50),
        "unit_price": unit_price,
        "quantity": quantity,
        "discount": discount,
        "status": status
    }


class StreamSimulator:
    def __init__(self, broker: str, topic: str, rate: int, count: int, dry_run: bool):
        self.broker = broker
        self.topic = topic
        self.rate = rate
        self.count = count
        self.dry_run = dry_run
        self.producer = None
        self._init_producer()

    def _init_producer(self):
        if self.dry_run:
            logger.info("[DRY RUN MODE] Simulating event production without Kafka broker connection.")
            return

        if not KAFKA_AVAILABLE:
            logger.warning("kafka-python library is not installed in local environment.")
            logger.warning("Running in simulation mode. To enable broker push: pip install kafka-python-ng")
            self.dry_run = True
            return

        try:
            logger.info(f"Connecting to Kafka/Redpanda broker at: {self.broker}...")
            self.producer = KafkaProducer(
                bootstrap_servers=[self.broker],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                request_timeout_ms=5000,
                retries=3
            )
            logger.info(f"Successfully connected to broker. Target topic: '{self.topic}'")
        except Exception as e:
            logger.warning(f"Could not connect to Kafka broker ({e}). Falling back to simulation mode.")
            self.dry_run = True

    def start(self):
        logger.info(f"Starting stream producer: Target Count = {self.count} events | Rate = {self.rate} msg/sec")
        start_time = time.time()
        produced_count = 0
        total_bytes = 0

        interval = 1.0 / max(self.rate, 1)

        try:
            for i in range(1, self.count + 1):
                order_id = int(time.time() * 1000) % 1000000000 + i
                event = generate_event(order_id)
                event_bytes = json.dumps(event).encode("utf-8")
                total_bytes += len(event_bytes)

                if self.producer and not self.dry_run:
                    self.producer.send(self.topic, value=event)
                
                produced_count += 1

                if produced_count % max(1, (self.count // 10)) == 0 or produced_count == self.count:
                    elapsed = time.time() - start_time
                    current_rate = round(produced_count / max(elapsed, 0.001), 1)
                    logger.info(f"Emitted {produced_count}/{self.count} events ({current_rate} msg/sec)")

                time.sleep(interval)

            if self.producer:
                self.producer.flush()

        except KeyboardInterrupt:
            logger.info("Stream production interrupted by user.")

        total_duration = round(time.time() - start_time, 2)
        avg_rate = round(produced_count / max(total_duration, 0.001), 1)

        print("\n" + "=" * 60)
        print(" REAL-TIME STREAMING SUMMARY")
        print("=" * 60)
        print(f" Target Topic      : {self.topic}")
        print(f" Total Events      : {produced_count}")
        print(f" Data Volume       : {round(total_bytes / 1024, 2)} KB")
        print(f" Execution Duration: {total_duration}s")
        print(f" Average Rate      : {avg_rate} msg/sec")
        print(f" Mode              : {'Simulated (Dry Run)' if self.dry_run else 'Published to Kafka'}")
        print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Real-Time Kafka Event Producer for Lakehouse Streaming (M02)")
    parser.add_argument("--broker", type=str, default=os.environ.get("KAFKA_BROKER", "localhost:9092"), help="Kafka broker host:port")
    parser.add_argument("--topic", type=str, default="enterprise.orders.events", help="Kafka destination topic")
    parser.add_argument("--rate", type=int, default=10, help="Target events per second (default: 10)")
    parser.add_argument("--count", type=int, default=50, help="Total events to produce (default: 50)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate event generation without broker push")

    args = parser.parse_args()
    sim = StreamSimulator(
        broker=args.broker,
        topic=args.topic,
        rate=args.rate,
        count=args.count,
        dry_run=args.dry_run
    )
    sim.start()


if __name__ == "__main__":
    main()
