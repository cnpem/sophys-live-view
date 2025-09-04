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
    parser.add_argument(
        "--show-stats-by-default",
        action="store_true",
        help="Show curve statistics by default on 1D plots.",
    )
    parser.add_argument(
        "--profile", action="store_true", help="Profile this application with py-spy."
    )

    args = parser.parse_args()

    if args.profile:
        import os
        import subprocess

        subprocess.Popen(f"py-spy record -o profile.svg --pid {os.getpid()}".split())

    app = QApplication()

    kafka_data_source = KafkaDataSource(
        args.topic, [args.bootstrap], hour_offset=args.hour_offset
    )

    main_window = SophysLiveView([kafka_data_source], args.show_stats_by_default)
    main_window.show()

    return app.exec_()


if __name__ == "__main__":
    entrypoint()
