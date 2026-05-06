import argparse
import logging
import logging.config
import sys

from qtpy.QtWidgets import QApplication

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
        "--tiled-url",
        default=None,
        type=str,
        help="Tiled URL to connect to (default: None - Do not connect to Tiled).",
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
    parser.add_argument(
        "--profile-memory",
        action="store_true",
        help="Profile this application with memray.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Log level for the logging module (default: INFO)",
    )

    args = parser.parse_args()

    if args.profile:
        import os
        import subprocess

        subprocess.Popen(f"py-spy record -o profile.svg --pid {os.getpid()}".split())

    def __inner():
        app = QApplication(sys.argv)

        if args.tiled_url:
            from .utils.tiled_data_source import TiledDataSource

            data_source = TiledDataSource(args.tiled_url, hour_offset=args.hour_offset)
        else:
            from .utils.kafka_data_source import KafkaDataSource

            data_source = KafkaDataSource(
                args.topic, [args.bootstrap], hour_offset=args.hour_offset
            )

        main_window = SophysLiveView([data_source], args.show_stats_by_default)
        main_window.show()

        return app.exec_()

    if args.profile_memory:
        import pathlib

        import memray

        pathlib.Path("profile.bin").unlink(missing_ok=True)
        with memray.Tracker("profile.bin"):
            _ret = __inner()

        print(
            "You can run something like 'memray flamegraph profile.bin' to generate a report on memory usage."
        )
        return _ret

    logging.config.dictConfig(
        {
            "version": 1,
            "formatters": {
                "basic": {
                    "format": "[%(asctime)s %(levelname)s - %(name)s] %(message)s",
                }
            },
            "handlers": {
                "stream": {
                    "class": "logging.StreamHandler",
                    "formatter": "basic",
                    "level": "DEBUG",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["stream"],
                    "level": logging.INFO,
                },
                "httpx": {
                    "handlers": ["stream"],
                    "level": logging.WARNING,
                },
                "sophys.live_view": {
                    "handlers": ["stream"],
                    "level": args.log_level,
                },
            },
        }
    )

    return __inner()


if __name__ == "__main__":
    entrypoint()
