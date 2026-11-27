"""Identify an individual vehicle from addressed CAN Mode 09 VIN replies."""

import hashlib
import re
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .obd_frames import _can_frame, _compact_hex


_VIN = re.compile(r"[A-HJ-NPR-Z0-9]{17}")
_MODELS = {
    ("19XFC2F6", "L"): ("2020 Honda Civic LX", "honda-civic"),
    ("2HGFC2F6", "L"): ("2020 Honda Civic LX", "honda-civic"),
    ("JTMP1RFV", "M"): ("2021 Toyota RAV4 XLE", "standard"),
}


@dataclass(frozen=True)
class Vehicle:
    vin: str | None
    status: str
    responders: tuple[str, ...]
    label: str
    profile: str

    @property
    def fingerprint(self) -> str | None:
        return hashlib.sha256(self.vin.encode("ascii")).hexdigest() if self.vin else None

    @property
    def file_tag(self) -> str:
        if not self.vin:
            return "unidentified"
        slug = re.sub(r"[^a-z0-9]+", "-", self.label.lower()).strip("-")[:48].rstrip("-") or "vehicle"
        return f"{slug}-{self.fingerprint[:12]}"

    def provenance(self) -> dict:
        return {"status": self.status, "source": "OBD 0902", "label": self.label,
                "vin_sha256": self.fingerprint, "responders": list(self.responders)}


def vehicle_profiles(config: Path | None) -> dict[str, tuple[str, str]]:
    if config is None:
        return {}
    with config.open("rb") as stream:
        entries = tomllib.load(stream).get("vehicles", {})
    if not isinstance(entries, dict):
        raise ValueError("Expected a [vehicles] table in the configuration.")
    profiles = {}
    for vin, entry in entries.items():
        if not _VIN.fullmatch(vin) or not isinstance(entry, dict) or entry.keys() - {"label", "profile"}:
            raise ValueError("Expected a 17-character uppercase VIN with label and optional profile under [vehicles].")
        label = entry.get("label")
        default = _MODELS.get((vin[:8], vin[9]), ("Vehicle", "standard"))[1]
        profile = entry.get("profile", default)
        if not isinstance(label, str) or not label.strip() or profile not in ("standard", "honda-civic"):
            raise ValueError("A vehicle entry needs a label and a standard or honda-civic polling profile.")
        profiles[vin] = (label.strip(), profile)
    return profiles


def _vin_from_frames(frames: list[bytes]) -> str | None:
    # 20 application bytes: 49 02, one data record, then the 17 ASCII characters.
    if len(frames) != 3:
        return None
    first, second, third = frames
    if (len(first) != 8 or first[:5] != b"\x10\x14\x49\x02\x01"
            or len(second) != 8 or second[0] != 0x21 or len(third) != 8 or third[0] != 0x22):
        return None
    raw = first[5:] + second[1:] + third[1:]
    vin = raw.decode("ascii", errors="replace")
    if not _VIN.fullmatch(vin) or len(set(vin)) == 1:
        return None
    return vin


def identify_vehicle(lines: tuple[bytes, ...], width: int, profiles: dict[str, tuple[str, str]]) -> Vehicle:
    frames: dict[str, list[bytes]] = defaultdict(list)
    for line in lines:
        compact = _compact_hex(line)
        parsed = _can_frame(compact, width) if compact else None
        if parsed:
            address, frame = parsed
            frames[address].append(frame)
    vins = {address: vin for address, parts in frames.items() if (vin := _vin_from_frames(parts)) is not None}
    distinct = set(vins.values())
    if len(distinct) != 1:
        status = "conflicting" if distinct else "unavailable"
        return Vehicle(None, status, tuple(sorted(vins)), "Unidentified vehicle", "standard")
    vin = distinct.pop()
    label, profile = profiles.get(vin, _MODELS.get((vin[:8], vin[9]), ("Vehicle", "standard")))
    return Vehicle(vin, "identified", tuple(sorted(vins)), label, profile)
