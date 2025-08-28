from abc import abstractmethod
from functools import partial

from event_model import DocumentRouter, Event, EventDescriptor, RunStart, RunStop
import numpy as np

from .data_source import DataSource


class DocumentParser(DocumentRouter):
    METADATA_KEYS = {"uid", "scan_id", "detectors", "motors"}

    def start(self, doc: RunStart):
        display_name = str(
            doc.get("metadata_save_file_identifier", doc.get("scan_id", "unknown"))
        )
        metadata = {key: doc[key] for key in self.METADATA_KEYS if key in doc}

        self.on_new_run_started(display_name, metadata)

    def descriptor(self, doc: EventDescriptor):
        start_uid = doc["run_start"]
        descriptor_uid = doc["uid"]
        fields = set(doc["data_keys"].keys())

        self.on_new_descriptor(start_uid, descriptor_uid, fields)

    def event(self, doc: Event):
        descriptor_uid = doc["descriptor"]
        values = doc["data"]
        timestamp = doc["time"]

        self.on_new_event(descriptor_uid, values, timestamp)

    def stop(self, doc: RunStop):
        pass

    @abstractmethod
    def on_new_run_started(self, display_name: str, metadata: dict):
        pass

    @abstractmethod
    def on_new_descriptor(self, start_uid: str, descriptor_uid: str, fields: set[str]):
        pass

    @abstractmethod
    def on_new_event(self, descriptor_uid: str, values: dict, timestamp: float):
        pass


class BlueskyDataSource(DataSource, DocumentParser):
    def __init__(self):
        DataSource.__init__(self)
        DocumentRouter.__init__(self)

        self._run_metadata = dict()
        self._descriptors = dict()

    def on_new_run_started(self, display_name: str, metadata: dict):
        uid = metadata["uid"]

        self._run_metadata[uid] = {"name": display_name, "metadata": metadata}

    def on_new_descriptor(self, start_uid: str, descriptor_uid: str, fields: set[str]):
        fields.add("timestamp")
        self._run_metadata[start_uid]["fields"] = fields

        self._descriptors[descriptor_uid] = start_uid

        self.new_data_stream.emit(
            start_uid,
            self._run_metadata[start_uid]["name"],
            fields,
            self._run_metadata[start_uid]["metadata"],
        )

    def on_new_event(self, descriptor_uid: str, values: dict, timestamp: float):
        start_uid = self._descriptors[descriptor_uid]

        received_data = {key: np.array([val]) for key, val in values.items()}
        received_data["timestamp"] = np.array([timestamp])

        self.new_data_received.emit(start_uid, received_data)

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
