from datetime import datetime, timedelta, timezone
import logging
import typing

from kafka import KafkaConsumer, TopicPartition
import msgpack

from .bluesky_data_source import BlueskyDataSource


class KafkaDataSource(BlueskyDataSource):
    def __init__(
        self,
        topic_name: str,
        bootstrap_servers: list[str],
        hour_offset: typing.Optional[int] = None,
    ):
        super().__init__()

        self._topic_name = topic_name
        self._bootstrap_servers = bootstrap_servers
        self._hour_offset = hour_offset

        self._logger = logging.getLogger("sophys.live_view.data_source.kafka")

        self._closed = False

    def run(self):
        consumer = KafkaConsumer(
            self._topic_name,
            bootstrap_servers=self._bootstrap_servers,
            value_deserializer=msgpack.unpackb,
            consumer_timeout_ms=250,
        )

        all_partitions = [
            TopicPartition(self._topic_name, p)
            for p in consumer.partitions_for_topic(self._topic_name)
        ]

        start_offset = 0
        if self._hour_offset:
            now = datetime.now(timezone.utc)
            hour_offset = int(
                (now - timedelta(hours=self._hour_offset)).timestamp() * 1000
            )
            timestamp_offsets = consumer.offsets_for_times(
                {p: hour_offset for p in all_partitions}
            )

            for partition, offset_ts in timestamp_offsets.items():
                if offset_ts is not None:
                    consumer.seek(partition, offset_ts.offset)
                    start_offset = offset_ts.offset

        end_offsets = consumer.end_offsets(all_partitions)
        current_offset = list(end_offsets.values())[0]

        while not self._closed:
            for message in consumer:
                if self._closed:
                    break

                self._logger.debug("Received new message: %s", str(message))

                done_preloading = message.offset + 1 >= current_offset
                self.go_to_last_automatically.emit(done_preloading)

                document_type, document = message.value

                if document_type in ("start", "event", "stop"):
                    if done_preloading:
                        completion_percent = 100.0
                    else:
                        completion_percent = (
                            100
                            * (message.offset - start_offset + 1)
                            / (current_offset - start_offset)
                        )
                    self.loading_status.emit(
                        "Loading runs from Kafka...", completion_percent
                    )

                self(document_type, document)

    def close_thread(self):
        self._closed = True
