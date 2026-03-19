from datetime import datetime, timedelta, timezone
import logging
import typing

from kafka import KafkaConsumer, TopicPartition
import msgpack_numpy as msgpack

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

    def _start_processing(self):
        self._consumer = KafkaConsumer(
            self._topic_name,
            bootstrap_servers=self._bootstrap_servers,
            value_deserializer=msgpack.unpackb,
            consumer_timeout_ms=250,
        )

        self._all_partitions = [
            TopicPartition(self._topic_name, p)
            for p in self._consumer.partitions_for_topic(self._topic_name)
        ]

        self._start_offset = 0
        if self._hour_offset:
            now = datetime.now(timezone.utc)
            hour_offset = int(
                (now - timedelta(hours=self._hour_offset)).timestamp() * 1000
            )
            timestamp_offsets = self._consumer.offsets_for_times(
                {p: hour_offset for p in self._all_partitions}
            )

            for partition, offset_ts in timestamp_offsets.items():
                if offset_ts is not None:
                    self._consumer.seek(partition, offset_ts.offset)
                    self._start_offset = offset_ts.offset

        end_offsets = self._consumer.end_offsets(self._all_partitions)
        self._current_offset = list(end_offsets.values())[0]

        super()._start_processing()

    def process(self):
        if self._closed:
            return

        sent_completed_status = False

        records = self._consumer.poll(timeout_ms=250)
        for partition in self._all_partitions:
            batched_messages = records.get(partition, tuple())
            for message in batched_messages:
                self._logger.debug("Received new message: %s", message)

                done_preloading = message.offset + 1 >= self._current_offset
                self.notify_go_to_last_automatically(done_preloading)

                document_type, document = message.value

                if not sent_completed_status and document_type in (
                    "start",
                    "event",
                    "stop",
                ):
                    if done_preloading:
                        completion_percent = 100.0
                        sent_completed_status = True
                    else:
                        completion_percent = (
                            100
                            * (message.offset - self._start_offset + 1)
                            / (self._current_offset - self._start_offset)
                        )
                    self.notify_loading_status(
                        "Loading runs from Kafka...", completion_percent
                    )

                self(document_type, document)

        incoming_bytes = (
            self._consumer.metrics()
            .get("consumer-metrics", {})
            .get("incoming-byte-rate", 0)
        )
        self._logger.debug(
            "Total received data in last 5s (kB): %.2f", incoming_bytes / 1024
        )

        self.dispatch_data.emit()
        self.reprocess.emit()

    def close_thread(self):
        self._closed = True

        super().close_thread()
