from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class FidelityLevel(StrEnum):
    F0 = "F0"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"


@dataclass(frozen=True)
class FieldFidelity:
    field: str
    level: FidelityLevel
    source: str
    transformed: bool = False
    note: str = ""

    def validate(self) -> None:
        if not self.field or not self.source:
            raise ValueError("field fidelity requires non-empty field and source")
        if self.level == FidelityLevel.F3 and self.transformed:
            raise ValueError("an exact F3 field cannot also be transformed")


@dataclass(frozen=True)
class DatasetFidelityManifest:
    dataset_id: str
    level: FidelityLevel
    source: str
    fields: tuple[FieldFidelity, ...]
    timestamp_status: str
    transformations: tuple[str, ...] = ()
    unsupported_claims: tuple[str, ...] = ()
    schema_version: str = "1.0"

    def validate(self) -> None:
        if not self.dataset_id or not self.source or not self.timestamp_status:
            raise ValueError("manifest identity, source, and timestamp status are required")
        for field_fidelity in self.fields:
            field_fidelity.validate()
        if self.level == FidelityLevel.F3 and self.transformations:
            raise ValueError("an F3 dataset cannot declare transformations")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DatasetFidelityManifest:
        manifest = cls(
            dataset_id=str(value["dataset_id"]),
            level=FidelityLevel(value["level"]),
            source=str(value["source"]),
            fields=tuple(
                FieldFidelity(
                    field=str(item["field"]),
                    level=FidelityLevel(item["level"]),
                    source=str(item["source"]),
                    transformed=bool(item.get("transformed", False)),
                    note=str(item.get("note", "")),
                )
                for item in value.get("fields", [])
            ),
            timestamp_status=str(value["timestamp_status"]),
            transformations=tuple(str(item) for item in value.get("transformations", [])),
            unsupported_claims=tuple(str(item) for item in value.get("unsupported_claims", [])),
            schema_version=str(value.get("schema_version", "1.0")),
        )
        manifest.validate()
        return manifest


@dataclass(frozen=True)
class TransformationEdit:
    message_index: int
    category: str
    start: int
    end: int
    original: str
    replacement: str
    source_content_hash: str


@dataclass(frozen=True)
class RequestLineage:
    request_id: str
    source_request_hash: str
    transformed_request_hash: str
    fidelity_level: FidelityLevel
    edits: tuple[TransformationEdit, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
