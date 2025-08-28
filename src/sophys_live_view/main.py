from qtpy.QtWidgets import QApplication

from .widgets.main_window import SophysLiveView


def entrypoint():
    app = QApplication()

    main_window = SophysLiveView()
    main_window.show()

    return app.exec_()


if __name__ == "__main__":
    entrypoint()
