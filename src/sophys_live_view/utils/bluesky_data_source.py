from abc import abstractmethod
from collections import defaultdict
from functools import partial

from event_model import DocumentRouter, Event, EventDescriptor, RunStart, RunStop
import numpy as np

from .data_source import DataSource


class DocumentParser(DocumentRouter):
    def start(self, doc: RunStart):
        display_name = str(doc.get("metadata_save_file_identifier", "unknown"))
        if display_name == "unknown":
            display_name = "scan " + str(doc.get("scan_id", "unknown"))

        self.on_new_run_started(display_name, doc)

    def descriptor(self, doc: EventDescriptor):
        start_uid = doc["run_start"]
        descriptor_uid = doc["uid"]
        fields = set(doc["data_keys"].keys())

        self.on_new_descriptor(start_uid, descriptor_uid, fields)

    def event(self, doc: Event):
        descriptor_uid = doc["descriptor"]
        values = doc["data"]
        timestamp = doc["time"]
        seq_num = doc["seq_num"]

        self.on_new_event(descriptor_uid, values, timestamp, seq_num)

    def stop(self, doc: RunStop):
        pass

    @abstractmethod
    def on_new_run_started(self, display_name: str, metadata: dict):
        pass

    @abstractmethod
    def on_new_descriptor(self, start_uid: str, descriptor_uid: str, fields: set[str]):
        pass

    @abstractmethod
    def on_new_event(
        self, descriptor_uid: str, values: dict, timestamp: float, seq_num: int
    ):
        pass


class BlueskyDataSource(DataSource, DocumentParser):
    def __init__(self):
        DataSource.__init__(self)
        DocumentRouter.__init__(self)

        self._run_metadata = dict()
        self._descriptors = dict()

    def on_new_run_started(self, display_name: str, metadata: dict):
        uid = metadata["uid"]

        self._run_metadata[uid] = {
            "name": display_name,
            "metadata": metadata,
            "grid_scan": "shape" in metadata,
        }

    def on_new_descriptor(self, start_uid: str, descriptor_uid: str, fields: set[str]):
        fields.add("timestamp")
        self._run_metadata[start_uid]["fields"] = fields

        detectors = set(self._run_metadata[start_uid]["metadata"].get("detectors", []))

        dimensions = self._run_metadata[start_uid]["metadata"]["hints"]["dimensions"]
        motors = list(v for x in dimensions for v in x[0])
        if len(motors) == 1 and "time" in motors:
            motors = ["timestamp"]

        self._descriptors[descriptor_uid] = start_uid

        self.new_data_stream.emit(
            start_uid,
            self._run_metadata[start_uid]["name"],
            fields,
            detectors,
            motors,
            self._run_metadata[start_uid]["metadata"],
        )

    def on_new_event(
        self, descriptor_uid: str, values: dict, timestamp: float, seq_num: int
    ):
        start_uid = self._descriptors[descriptor_uid]

        received_data = {key: np.array([val]) for key, val in values.items()}

        start_metadata = self._run_metadata[start_uid]["metadata"]
        metadata = defaultdict(lambda: dict())

        if self._run_metadata[start_uid]["grid_scan"]:
            shape = start_metadata.get("shape", (0, 0))
            snaking = start_metadata.get(
                "snaking", [start_metadata.get("snake_axes", False)] * 2
            )

            pos = list(np.unravel_index(seq_num - 1, shape))
            if snaking[1] and pos[0] % 2:
                pos[1] = shape[1] - pos[1] - 1

            position = tuple(map(int, pos))

            for key in start_metadata["detectors"]:
                metadata[key]["position"] = position

        received_data["timestamp"] = np.array([timestamp])

        self.new_data_received.emit(start_uid, received_data, metadata)

    def __getattribute__(self, attr_name):
        if attr_name == "start":
            return partial(DocumentParser.start, self)
        if attr_name == "event":
            return partial(DocumentParser.event, self)
        if attr_name == "stop":
            return partial(DocumentParser.stop, self)
        return super().__getattribute__(attr_name)

    def start_thread(self):
        """Needed because DocumentParser overrides the 'start' method."""
        DataSource.start(self)
