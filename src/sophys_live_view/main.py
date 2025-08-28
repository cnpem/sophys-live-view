import argparse

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
    args = parser.parse_args()

    app = QApplication()

    main_window = SophysLiveView(args.topic, [args.bootstrap])
    main_window.show()

    return app.exec_()


if __name__ == "__main__":
    entrypoint()
