import logging

from kafka import KafkaConsumer
import msgpack

from .bluesky_data_source import BlueskyDataSource


class KafkaDataSource(BlueskyDataSource):
    def __init__(self, topic_name: str, bootstrap_servers: list[str]):
        super().__init__()

        self._topic_name = topic_name
        self._bootstrap_servers = bootstrap_servers

        self._logger = logging.getLogger("sophys.live_view.data_source.kafka")

    def run(self):
        consumer = KafkaConsumer(
            self._topic_name,
            bootstrap_servers=self._bootstrap_servers,
            value_deserializer=msgpack.unpackb,
        )

        for message in consumer:
            self._logger.debug("Received new message: %s", str(message))

            document_type, document = message.value
            self(document_type, document)
