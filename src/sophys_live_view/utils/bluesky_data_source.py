from abc import abstractmethod
from collections import defaultdict
import typing

from event_model import DocumentRouter, Event, EventDescriptor, RunStart, RunStop
import numpy as np

from .data_source import BatchReceivedDataSource


class DocumentParser(DocumentRouter):
    def start(self, doc: RunStart):
        display_name = str(doc.get("metadata_save_file_identifier", "unknown"))
        if display_name == "unknown":
            display_name = "scan " + str(doc.get("scan_id", "unknown"))
            if "plan_name" in doc:
                display_name += " ({})".format(doc.get("plan_name"))

        if "file_name" in doc:
            display_name += " - {}".format(doc.get("file_name"))

        self.on_new_run_started(display_name, doc)

    def descriptor(self, doc: EventDescriptor):
        start_uid = doc["run_start"]
        descriptor_uid = doc["uid"]
        descriptor_name = doc["name"]

        fields = set()
        fields_name_map = dict()
        for field, field_info in doc["data_keys"].items():
            if "units" in field_info and field_info["units"] != "":
                fields_name_map[field] = "{} ({})".format(field, field_info["units"])

            fields.add(field)

        extra_metadata = dict()
        for signal, data in doc["configuration"].items():
            extra_metadata[signal] = data["data"]

        self.on_new_descriptor(
            start_uid,
            descriptor_uid,
            descriptor_name,
            fields,
            fields_name_map,
            extra_metadata,
        )

    def event(self, doc: Event):
        descriptor_uid = doc["descriptor"]
        values = doc["data"]
        timestamp = doc["time"]
        seq_num = doc["seq_num"]

        self.on_new_event(descriptor_uid, values, timestamp, seq_num)

    def stop(self, doc: RunStop):
        self.on_run_ended(doc["run_start"])

    @abstractmethod
    def on_new_run_started(self, display_name: str, metadata: dict):
        pass

    @abstractmethod
    def on_new_descriptor(
        self,
        start_uid: str,
        descriptor_uid: str,
        descriptor_name: str,
        fields: set[str],
        fields_name_map: dict[str, str],
        extra_metadata: dict[str, dict[str, typing.Any]],
    ):
        pass

    @abstractmethod
    def on_new_event(
        self, descriptor_uid: str, values: dict, timestamp: float, seq_num: int
    ):
        pass

    @abstractmethod
    def on_run_ended(self, start_uid):
        pass


class BlueskyDataSource(BatchReceivedDataSource):
    def __init__(self):
        super().__init__()

        self._run_metadata = dict()
        self._descriptors = dict()

        self._parser = DocumentParser()
        self._parser.on_new_run_started = self.on_new_run_started
        self._parser.on_new_descriptor = self.on_new_descriptor
        self._parser.on_new_event = self.on_new_event
        self._parser.on_run_ended = self.on_run_ended

    def on_new_run_started(self, display_name: str, metadata: dict):
        uid = metadata["uid"]

        self._run_metadata[uid] = {
            "name": display_name,
            "metadata": metadata,
            "grid_scan": "shape" in metadata,
        }

    def on_new_descriptor(
        self,
        start_uid: str,
        descriptor_uid: str,
        descriptor_name: str,
        fields: set[str],
        fields_name_map: dict[str, str],
        extra_metadata: dict[str, dict[str, typing.Any]],
    ):
        # TODO: Support other streams
        if descriptor_name != "primary":
            return

        fields.add("time")
        fields.add("seq_num")
        self._run_metadata[start_uid]["fields"] = fields

        fields_name_map["time"] = "time (s)"

        detectors = set(self._run_metadata[start_uid]["metadata"].get("detectors", []))

        motors = ["time"]
        if "hints" in self._run_metadata[start_uid]["metadata"]:
            dimensions = self._run_metadata[start_uid]["metadata"]["hints"][
                "dimensions"
            ]
            motors = list(v for x in dimensions for v in x[0])

        metadata = self._run_metadata[start_uid]["metadata"]
        metadata["configuration"] = extra_metadata

        self._descriptors[descriptor_uid] = start_uid

        self.notify_new_data_stream(
            start_uid,
            self._run_metadata[start_uid]["name"],
            fields,
            fields_name_map,
            detectors,
            motors,
            metadata,
        )

    def on_new_event(
        self, descriptor_uid: str, values: dict, timestamp: float, seq_num: int
    ):
        start_uid = self._descriptors.get(descriptor_uid, None)
        if start_uid is None:
            return

        received_data = {key: [val] for key, val in values.items()}

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
                metadata[key]["position"] = [position]

        received_data["time"] = [timestamp - start_metadata.get("time", 0)]
        received_data["seq_num"] = [seq_num]

        self.notify_new_data_received(start_uid, 1, received_data, metadata)

    def on_run_ended(self, start_uid):
        self.notify_data_stream_closed(start_uid)

    def __call__(self, name, doc):
        return self._parser(name, doc)
