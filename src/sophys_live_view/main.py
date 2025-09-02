import argparse

from qtpy.QtWidgets import QApplication

from .utils.kafka_data_source import KafkaDataSource
from .widgets.main_window import SophysLiveView


def entrypoint():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--topic",
        default="test_bluesky_raw_docs",
        help="Kafka topic to subscribe to (default: test_bluesky_raw_docs).",
    )
    parser.add_argument(
        "-b",
        "--bootstrap",
        default="localhost:60612",
        help="Kafka bootstrap server to use (default: localhost:60612).",
    )
    parser.add_argument(
        "--hour-offset",
        default=None,
        type=float,
        help="Retrieve X hours before the current time from Kafka.",
    )

    args = parser.parse_args()

    app = QApplication()

    kafka_data_source = KafkaDataSource(
        args.topic, [args.bootstrap], hour_offset=args.hour_offset
    )

    main_window = SophysLiveView([kafka_data_source])
    main_window.show()

    return app.exec_()


if __name__ == "__main__":
    entrypoint()
