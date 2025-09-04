import json
import pathlib

from .bluesky_data_source import BlueskyDataSource


class JSONDataSource(BlueskyDataSource):
    def __init__(self, file_path: str):
        super().__init__()

        self._file_path = pathlib.Path(file_path)

    def run(self):
        self.loading_status.emit("Loading JSON file...", 0.0)

        file_contents = None
        with open(self._file_path) as _f:
            file_contents = json.load(_f)

        for document_type, document in file_contents:
            self(document_type, document)

        self.loading_status.emit("Loading JSON file...", 100.0)
