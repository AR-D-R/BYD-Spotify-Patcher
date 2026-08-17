#!/usr/bin/env python3
"""BYD Spotify Patcher v0.5.3.

Patches a user-supplied Spotify 8.9.76.538 APK so multiple fixed clone
identities can coexist with BYD's factory ``com.spotify.music`` installation.

The tool never downloads or bundles Spotify. It only transforms an APK selected
by the user on their own computer.

Core patch profile:
* fixed primary/secondary package identities (musib / musia)
* binary manifest identity/provider/permission patching in-place
* package-scoped resources.arsc provider authority patching
* exact DEX package/process string patching plus DEX SHA-1/Adler32 repair
* preserve META-INF/services; remove only obsolete signature metadata
* stable v9 Left and v14 Right BYD wide-screen UI profiles
* editable visible app label plus optional launcher-icon hue shift
* proven BYD RESTORE_PLAYBACK MediaBrowser auto-resume helper (logic unchanged)
* construct a 4-byte aligned APK and sign with a reusable per-user key

Both supported clone identities, ``com.spotify.musib`` and ``com.spotify.musia``,
pass the tested DEX lexical-order checks.
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import zipfile
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw

APP_VERSION = "0.5.3"
SUPPORTED_SPOTIFY_VERSION = "8.9.76.538"
SUPPORTED_SPOTIFY_VERSION_CODE = 119017142
WIDE_LAYOUT_PATH = "res/layout-w600dp-v13/adaptive_main.xml"
WIDE_LAYOUT_BASE_SHA256 = "9e25d64fdfd097a1fe544af86439fe674942911fc7f6a12a2ea99321a4a7027e"
PANEL_LEFT = "left"
PANEL_RIGHT = "right"
OLD_PKG = "com.spotify.music"
NEW_PKG = "com.spotify.musib"  # primary/default package; same length as OLD_PKG
INSTANCE_PRIMARY = "primary"
INSTANCE_SECONDARY = "secondary"
MAX_APP_LABEL_LEN = 24
INSTANCE_CONFIG = {
    INSTANCE_PRIMARY: {
        "title": "Primary",
        "package": "com.spotify.musib",
        "label": "SpotifyPlus",
        "output_suffix": "",
        "hue": 0,
    },
    INSTANCE_SECONDARY: {
        "title": "Secondary",
        "package": "com.spotify.musia",
        "label": "SpotifyPlus-S",
        "output_suffix": "_S",
        "hue": 110,
    },
}

KNOWN_MANIFEST_EXACT = [
    OLD_PKG,
    OLD_PKG + ".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
    OLD_PKG + ".permission.C2D_MESSAGE",
    OLD_PKG + ".permission.INTERNAL_BROADCAST",
    OLD_PKG + ".permission.SECURED_BROADCAST",
    OLD_PKG + ".androidx-startup",
    OLD_PKG + ".share",
    OLD_PKG + ".pushnotificationsv2",
    OLD_PKG + ".profile",
    OLD_PKG + ".vtec",
    OLD_PKG + ".calimage",
    OLD_PKG + ".early-initialization",
    OLD_PKG + ".imagepicker",
    OLD_PKG + ".sso.afterlogindummytask",
]

RESOURCE_AUTHORITY_OLD = b"com.spotify.mobile.android.mediaapi"

# Tiny helper DEX payloads contain only BYD Spotify Patcher code, never Spotify code.
# They are embedded so the public patcher remains a single-source application.
LTR_FRAME_DEX_B64 = "ZGV4CjAzNQAHdFOsL3DK23Z4dZJg0aTmnjI3P/uruWCIAwAAcAAAAHhWNBIAAAAAAAAAAAADAAAPAAAAcAAAAAcAAACsAAAABgAAAMgAAAAAAAAAAAAAAAkAAAAQAQAAAQAAAFgBAAAQAgAAeAEAAHgBAACAAQAAgwEAAJ4BAAC7AQAA0AEAAO4BAAASAgAAFQIAABkCAAAdAgAAIgIAACgCAAAuAgAAOwIAAAEAAAACAAAAAwAAAAQAAAAFAAAABgAAAAcAAAAHAAAABgAAAAAAAAAIAAAABgAAAFACAAAJAAAABgAAAFgCAAAKAAAABgAAAGACAAALAAAABgAAAGgCAAAJAAAABgAAAHQCAAADAAEADgAAAAQAAgAAAAAABAADAAAAAAAEAAQAAAAAAAQABQANAAAABQACAAAAAAAFAAMAAAAAAAUABAAAAAAABQAFAA0AAAAFAAAAAQAAAAQAAAAAAAAA/////wAAAADkAgAAAAAAAAY8aW5pdD4AAUkAGUxhbmRyb2lkL2NvbnRlbnQvQ29udGV4dDsAG0xhbmRyb2lkL3V0aWwvQXR0cmlidXRlU2V0OwATTGFuZHJvaWQvdmlldy9WaWV3OwAcTGFuZHJvaWQvd2lkZ2V0L0ZyYW1lTGF5b3V0OwAiTGNvbS9zcG90aWZ5L211c2liL0x0ckZyYW1lTGF5b3V0OwABVgACVkkAAlZMAANWTEwABFZMTEkABFZMTEwAC29uVmlld0FkZGVkABJzZXRMYXlvdXREaXJlY3Rpb24AAAEAAAAAAAAAAQAAAAEAAAACAAAAAQACAAMAAAABAAIAAAAAAAEAAAADAAAAAgACAAIAAAAAAAAABAAAAHAgAQAQAA4AAwADAAMAAAAAAAAABAAAAHAwAgAQAg4ABAAEAAQAAAAAAAAABAAAAHBAAwAQMg4AAwACAAIAAAAAAAAACAAAAG8gBAAhABIAbiAAAAIADgAAAAMBBYGABPwEAYGABJQFAYGABKwFCAHEBQAACwAAAAAAAAABAAAAAAAAAAEAAAAPAAAAcAAAAAIAAAAHAAAArAAAAAMAAAAGAAAAyAAAAAUAAAAJAAAAEAEAAAYAAAABAAAAWAEAAAIgAAAPAAAAeAEAAAEQAAAFAAAAUAIAAAEgAAAEAAAAfAIAAAAgAAABAAAA5AIAAAAQAAABAAAAAAMAAA=="
AUTO_RESUME_DEX_B64 = "ZGV4CjAzNQAOJkXgrtfeY5Z20w1kGWVAfnX9EilkbDxICwAAcAAAAHhWNBIAAAAAAAAAALQKAAA+AAAAcAAAABgAAABoAQAAEgAAAMgBAAADAAAAoAIAAB0AAAC4AgAAAgAAAKADAABoBwAA4AMAAOADAADoAwAA6wMAAPEDAAD0AwAA+AMAAPwDAAAgBAAAPAQAAF8EAACCBAAAmQQAALoEAADVBAAA7wQAABUFAABNBQAAcgUAAK0FAADWBQAAAgYAABcGAAAtBgAAVwYAAH4GAACYBgAArAYAAMAGAADTBgAA6QYAAOwGAADxBgAA9QYAAPoGAAAABwAABwcAAAsHAAAOBwAAFwcAAB4HAABlBwAAbgcAAIkHAACVBwAAowcAALcHAADIBwAA2gcAAPAHAAD2BwAABAgAAAwIAAAZCAAAIwgAADMIAAA5CAAAQggAAFMIAABhCAAAdQgAAIYIAACWCAAAAQAAAAYAAAAHAAAACAAAAAkAAAAKAAAACwAAAAwAAAANAAAADgAAAA8AAAAQAAAAEQAAABIAAAATAAAAFAAAABUAAAAWAAAAFwAAABgAAAAZAAAAGgAAAB0AAAAkAAAAAgAAAAAAAADcCAAABAAAAAEAAACgCAAABQAAAAEAAADwCAAAAwAAAAIAAAAAAAAAAwAAAAkAAAAAAAAAAwAAAAwAAAAAAAAAAwAAAA4AAAAAAAAABQAAABAAAADUCAAABQAAABQAAAD4CAAAHQAAABYAAAAAAAAAHgAAABYAAACoCAAAHwAAABYAAACwCAAAIgAAABYAAAC4CAAAIAAAABYAAADECAAAIAAAABYAAADMCAAAHwAAABYAAADoCAAAIQAAABYAAAAACQAAIwAAABYAAAAMCQAACQAAADAAAAARABIANwAAABIACwAlAAAAAQAOAAAAAAABAAMAJgAAAAEAAgA4AAAAAQABADkAAAADABAAAAAAAAQACwApAAAABQAJAAAAAAAFAAkANAAAAAUACgA7AAAABQARADwAAAAFAAkAPQAAAAYADgAAAAAABwAEACwAAAAHAAgALgAAAAoACQAAAAAACwAMAAAAAAALAAkAKAAAAAsACQAqAAAACwAGAC0AAAAMAAkANgAAAA0ADQAAAAAADQAFAC8AAAARAA8AAAAAABEACQAzAAAAEgAJAAAAAAASAAkAKwAAABIABwAyAAAAEgAJADQAAAASAAAANQAAABEAAAARAAAACgAAAAAAAAD/////AAAAAKIKAAAAAAAAEgAAAAEAAAAFAAAAAAAAAP////8AAAAAhgoAAAAAAAAGPGluaXQ+AAFJAARJTElJAAFMAAJMSQACTEwAIkxhbmRyb2lkL2FwcC9Ob3RpZmljYXRpb24kQnVpbGRlcjsAGkxhbmRyb2lkL2FwcC9Ob3RpZmljYXRpb247ACFMYW5kcm9pZC9hcHAvTm90aWZpY2F0aW9uQ2hhbm5lbDsAIUxhbmRyb2lkL2FwcC9Ob3RpZmljYXRpb25NYW5hZ2VyOwAVTGFuZHJvaWQvYXBwL1NlcnZpY2U7AB9MYW5kcm9pZC9jb250ZW50L0NvbXBvbmVudE5hbWU7ABlMYW5kcm9pZC9jb250ZW50L0NvbnRleHQ7ABhMYW5kcm9pZC9jb250ZW50L0ludGVudDsAJExhbmRyb2lkL2NvbnRlbnQvcG0vQXBwbGljYXRpb25JbmZvOwA2TGFuZHJvaWQvbWVkaWEvYnJvd3NlL01lZGlhQnJvd3NlciRDb25uZWN0aW9uQ2FsbGJhY2s7ACNMYW5kcm9pZC9tZWRpYS9icm93c2UvTWVkaWFCcm93c2VyOwA5TGFuZHJvaWQvbWVkaWEvc2Vzc2lvbi9NZWRpYUNvbnRyb2xsZXIkVHJhbnNwb3J0Q29udHJvbHM7ACdMYW5kcm9pZC9tZWRpYS9zZXNzaW9uL01lZGlhQ29udHJvbGxlcjsAKkxhbmRyb2lkL21lZGlhL3Nlc3Npb24vTWVkaWFTZXNzaW9uJFRva2VuOwATTGFuZHJvaWQvb3MvQnVuZGxlOwAUTGFuZHJvaWQvb3MvSUJpbmRlcjsAKExjb20vc3BvdGlmeS9tdXNpYi9BdXRvUmVzdW1lQ29ubmVjdGlvbjsAJUxjb20vc3BvdGlmeS9tdXNpYi9BdXRvUmVzdW1lU2VydmljZTsAGExqYXZhL2xhbmcvQ2hhclNlcXVlbmNlOwASTGphdmEvbGFuZy9PYmplY3Q7ABJMamF2YS9sYW5nL1N0cmluZzsAEVJlc3VtaW5nIFNwb3RpZnkrABRTcG90aWZ5KyBBdXRvIFJlc3VtZQABVgADVklMAAJWTAADVkxMAARWTExJAAVWTExMTAACVloAAVoAB2Jyb3dzZXIABWJ1aWxkAEVjb20uc3BvdGlmeS5tdXNpYy5saWJzLm1lZGlhYnJvd3NlcnNlcnZpY2UuU3BvdGlmeU1lZGlhQnJvd3NlclNlcnZpY2UAB2Nvbm5lY3QAGWNyZWF0ZU5vdGlmaWNhdGlvbkNoYW5uZWwACmRpc2Nvbm5lY3QADGZpbmlzaFJlc3VtZQASZ2V0QXBwbGljYXRpb25JbmZvAA9nZXRTZXNzaW9uVG9rZW4AEGdldFN5c3RlbVNlcnZpY2UAFGdldFRyYW5zcG9ydENvbnRyb2xzAARpY29uAAxub3RpZmljYXRpb24ABm9uQmluZAALb25Db25uZWN0ZWQACG9uQ3JlYXRlAA5vblN0YXJ0Q29tbWFuZAAEcGxheQAHc2VydmljZQAPc2V0Q29udGVudFRpdGxlAAxzZXRTbWFsbEljb24AEnNwb3RpZnlfYXV0b3Jlc3VtZQAPc3RhcnRGb3JlZ3JvdW5kAA5zdG9wRm9yZWdyb3VuZAAIc3RvcFNlbGYAAQAAAAAAAAACAAAAAAACAAEAAAADAAAABAAAAAcABgAKAA8AAgAAAAcADgACAAAABwAVAAEAAAAIAAAAAwAAAAgAAAAAAAAAAQAAABIAAAABAAAAEwAAAAEAAAAVAAAAAwAAABUAEwAAAAAAAQAAABcAAAABAAEAAQAAAAAAAAAEAAAAcBAGAAAADgAHAAEABAAAAAAAAAA3AAAAbxAHAAYAIgADABoBOgAaAhwAEhNwQAQAEDIaATEAbiANABYADAEfAQQAbiAFAAEAbhAMAAYADAJSIwAAIgABABoBOgBwMAAAYAFuIAMAMAAaARsAbiACABAAbhABAAAADAETAuEQbjAIACYBDgAAAAMAAgAAAAAAAAAAAAIAAAASABEACgAEAAUAAAAAAAAAGQAAACIABgAaAScAcDALAGABIgERAHAgFgBhABIDIgILAHBTDwBiEFtiAgBuEBAAAgASIA8AAAACAAEAAgAAAAAAAAAIAAAAEhBuIAkAAQBuEAoAAQAOAAIAAgABAAAAAAAAAAYAAABwEA4AAABbAQEADgAIAAEAAwAAAAAAAAAbAAAAVHABAFQBAgBuEBIAAQAMAiIDDQBwMBQAAwJuEBUAAwAMBG4QEwAEAG4QEQABAG4QGQAAAA4AAAEBBAIBGIGABJQSGQGEFAEBrBMBAawSAQHAEwABAQEBEhaBgASkFBcBwBQAAAwAAAAAAAAAAQAAAAAAAAABAAAAPgAAAHAAAAACAAAAGAAAAGgBAAADAAAAEgAAAMgBAAAEAAAAAwAAAKACAAAFAAAAHQAAALgCAAAGAAAAAgAAAKADAAACIAAAPgAAAOADAAABEAAADQAAAKAIAAABIAAABwAAABQJAAAAIAAAAgAAAIYKAAAAEAAAAQAAALQKAAA="

APP_NAME_RID = 0x7F130116
ADAPTIVE_FOREGROUND_RID = 0x7F080782
NEW_APP_LABEL = "SpotifyPlus"
OLD_ADAPTIVE_FOREGROUND_PATH = "res/drawable/ic_launcher_renaissance_foreground.xml"
NEW_ADAPTIVE_FOREGROUND_PATH = "res/drawable/ic_launcher_renaissance_foreground.png"
DENSITY_ICON_PATHS = [
    "res/mipmap-mdpi-v4/ic_launcher_renaissance.webp",
    "res/mipmap-hdpi-v4/ic_launcher_renaissance.webp",
    "res/mipmap-xhdpi-v4/ic_launcher_renaissance.webp",
    "res/mipmap-xxhdpi-v4/ic_launcher_renaissance.webp",
    "res/mipmap-xxxhdpi-v4/ic_launcher_renaissance.webp",
]

SIGNATURE_RE = re.compile(r"META-INF/[^/]+\.(SF|RSA|DSA|EC)$", re.I)
DEX_MAGIC_PREFIX = b"dex\n"


class PatchError(RuntimeError):
    pass


def get_instance_config(instance: str) -> dict:
    key = (instance or INSTANCE_PRIMARY).lower().strip()
    if key not in INSTANCE_CONFIG:
        raise PatchError(f"Unknown app instance: {instance!r}")
    return INSTANCE_CONFIG[key]


def validate_app_label(label: str) -> str:
    label = (label or "").strip()
    if not label:
        raise PatchError("App display name cannot be empty")
    if len(label) > MAX_APP_LABEL_LEN:
        raise PatchError(f"App display name must be {MAX_APP_LABEL_LEN} characters or fewer")
    if any(ch in label for ch in "\r\n\x00"):
        raise PatchError("App display name cannot contain line breaks or NUL characters")
    return label


def normalise_hue(value: int | float) -> int:
    try:
        return int(round(float(value))) % 360
    except (TypeError, ValueError) as e:
        raise PatchError("Icon hue must be a number from 0 to 359 degrees") from e


def _resource_replacements(new_pkg: str) -> dict[bytes, bytes]:
    if len(new_pkg) != len(OLD_PKG):
        raise PatchError("Alternate package must be the same length as com.spotify.music")
    new = (new_pkg + ".android.mediaapi_").encode("ascii")
    if len(new) != len(RESOURCE_AUTHORITY_OLD):
        raise PatchError("Generated media-api provider authority has the wrong length")
    return {RESOURCE_AUTHORITY_OLD: new}


def _special_manifest_replacements(new_pkg: str) -> dict[str, str]:
    leaf = new_pkg.rsplit(".", 1)[-1]
    return {"androidx.car.app.connection": f"{leaf}xxx.car.app.connection"}


@dataclass
class DexAnalysis:
    name: str
    exact_package_occurrences: int = 0
    package_string_id_indexes: list[int] = field(default_factory=list)
    sort_safe: bool = True
    neighbours: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ApkAnalysis:
    input_path: Path
    input_sha256: str
    size_bytes: int
    spotify_version: str | None
    spotify_version_code: int | None
    profile_name: str
    wide_layout_sha256: str | None
    dex_count: int
    native_abis: list[str]
    services: list[str]
    manifest_patch_count: int
    unknown_manifest_strings: list[str]
    resource_matches: dict[str, int]
    dex: list[DexAnalysis]
    target_package: str
    compatible: bool
    warnings: list[str]

    @property
    def total_dex_package_occurrences(self) -> int:
        return sum(d.exact_package_occurrences for d in self.dex)


@dataclass
class PatchReport:
    input_path: Path
    output_path: Path
    input_sha256: str
    output_sha256: str
    panel_side: str
    instance: str
    package_name: str
    app_label: str
    icon_hue: int
    manifest_changes: list[tuple[str, str]]
    dex_changes: dict[str, int]
    resource_changes: dict[str, int]
    ui_changes: int
    services_preserved: int
    removed_signatures: list[str]
    warnings: list[str]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _read_utf16_len(buf: bytes | bytearray, off: int) -> tuple[int, int]:
    x = struct.unpack_from("<H", buf, off)[0]
    if x & 0x8000:
        y = struct.unpack_from("<H", buf, off + 2)[0]
        return (((x & 0x7FFF) << 16) | y), 4
    return x, 2


def _read_uleb128(data: bytes, off: int) -> tuple[int, int]:
    value = 0
    shift = 0
    for i in range(5):
        if off + i >= len(data):
            raise PatchError("Truncated ULEB128 in DEX")
        b = data[off + i]
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, i + 1
        shift += 7
    raise PatchError("Invalid ULEB128 in DEX")


def _dex_string_asciiish(data: bytes, string_data_off: int) -> str:
    """Decode enough of a DEX MUTF-8 string for lexical diagnostics.

    Spotify package/action strings around the package marker are ordinary ASCII.
    For unusual neighbouring strings, replacement decoding is diagnostic only;
    the patcher still validates the exact package's position before editing.
    """
    _utf16_len, n = _read_uleb128(data, string_data_off)
    start = string_data_off + n
    end = data.find(b"\x00", start)
    if end < 0:
        raise PatchError("Unterminated DEX string_data_item")
    raw = data[start:end]
    # MUTF-8 encodes U+0000 as C0 80. It is irrelevant for our ASCII package
    # names but replacing it makes diagnostics less surprising.
    raw = raw.replace(b"\xC0\x80", b"\x00")
    return raw.decode("utf-8", errors="replace")


def _dex_string_table(data: bytes) -> tuple[int, int, list[int]]:
    if len(data) < 112 or not data.startswith(DEX_MAGIC_PREFIX):
        raise PatchError("Not a recognised DEX file")
    string_ids_size, string_ids_off = struct.unpack_from("<II", data, 56)
    end = string_ids_off + string_ids_size * 4
    if string_ids_off < 112 or end > len(data):
        raise PatchError("DEX string_ids table is outside the file")
    offsets = list(struct.unpack_from("<" + "I" * string_ids_size, data, string_ids_off))
    return string_ids_size, string_ids_off, offsets


def analyse_dex(name: str, data: bytes, new_pkg: str = NEW_PKG) -> DexAnalysis:
    result = DexAnalysis(name=name)
    try:
        _size, _off, offsets = _dex_string_table(data)
        strings: dict[int, str] = {}
        indexes: list[int] = []
        for idx, s_off in enumerate(offsets):
            # Fast test: exact package is ASCII and short, so only decode strings
            # whose raw bytes can plausibly contain it.
            try:
                _n, leb_len = _read_uleb128(data, s_off)
                start = s_off + leb_len
            except Exception:
                continue
            if data[start:start + len(OLD_PKG)] == OLD_PKG.encode("ascii") and data[start + len(OLD_PKG):start + len(OLD_PKG) + 1] == b"\x00":
                s = _dex_string_asciiish(data, s_off)
                if s == OLD_PKG:
                    indexes.append(idx)
                    strings[idx] = s
        result.package_string_id_indexes = indexes
        result.exact_package_occurrences = len(indexes)

        for idx in indexes:
            prev_s = _dex_string_asciiish(data, offsets[idx - 1]) if idx > 0 else ""
            next_s = _dex_string_asciiish(data, offsets[idx + 1]) if idx + 1 < len(offsets) else "\U0010ffff"
            safe = (not prev_s or prev_s < new_pkg) and (not next_s or new_pkg < next_s)
            result.sort_safe &= safe
            result.neighbours.append(f"{prev_s!r} < {new_pkg!r} < {next_s!r} => {'OK' if safe else 'UNSAFE'}")
    except Exception as e:
        result.error = str(e)
        result.sort_safe = False
    return result


def _manifest_replacements(new_pkg: str = NEW_PKG) -> dict[str, str]:
    if len(new_pkg) != len(OLD_PKG):
        raise PatchError("Alternate package must be the same length as com.spotify.music")
    d = {s: s.replace(OLD_PKG, new_pkg, 1) for s in KNOWN_MANIFEST_EXACT}
    d.update(_special_manifest_replacements(new_pkg))
    for old, new in d.items():
        if len(old) != len(new):
            raise AssertionError(f"Replacement length mismatch: {old!r} -> {new!r}")
    return d


def _scan_binary_manifest(data: bytes) -> tuple[list[str], bool]:
    if len(data) < 36:
        raise PatchError("AndroidManifest.xml is unexpectedly small")
    pos = 8
    typ, header_size, _chunk_size = struct.unpack_from("<HHI", data, pos)
    if typ != 0x0001:
        raise PatchError(f"Expected binary XML string pool at offset 8, got type {typ:#x}")
    string_count, _style_count, flags, strings_start, _styles_start = struct.unpack_from(
        "<IIIII", data, pos + 8
    )
    if flags & 0x100:
        raise PatchError("UTF-8 AndroidManifest.xml string pool is not supported yet")
    offsets = struct.unpack_from("<" + "I" * string_count, data, pos + header_size)
    strings: list[str] = []
    for rel_off in offsets:
        start = pos + strings_start + rel_off
        n_chars, len_bytes = _read_utf16_len(data, start)
        payload_start = start + len_bytes
        payload_end = payload_start + n_chars * 2
        strings.append(bytes(data[payload_start:payload_end]).decode("utf-16le"))
    return strings, OLD_PKG in strings


def _unknown_manifest_strings(strings: list[str]) -> list[str]:
    known = set(KNOWN_MANIFEST_EXACT)
    unknown: list[str] = []
    for s in sorted(set(strings)):
        if not s.startswith(OLD_PKG + ".") or s in known:
            continue
        suffix = s[len(OLD_PKG) + 1 :]
        # Implementation classes and custom actions must not be renamed blindly.
        # A Java/Kotlin component name normally contains a capitalised class segment;
        # package-scoped authorities/permissions are typically all-lowercase.
        segments = suffix.split(".")
        looks_like_component_class = any(seg[:1].isupper() for seg in segments)
        if suffix and suffix[0].islower() and not looks_like_component_class and not (
            ".action." in suffix or suffix.startswith("service.") or suffix == "githash"
        ):
            unknown.append(s)
    return unknown


def patch_binary_manifest(data: bytes, new_pkg: str = NEW_PKG) -> tuple[bytes, list[tuple[str, str]], list[str]]:
    repl = _manifest_replacements(new_pkg)
    b = bytearray(data)
    strings, has_pkg = _scan_binary_manifest(data)
    if not has_pkg:
        raise PatchError("Input does not look like a normal com.spotify.music APK")

    pos = 8
    _typ, header_size, _chunk_size = struct.unpack_from("<HHI", b, pos)
    string_count, _style_count, flags, strings_start, _styles_start = struct.unpack_from(
        "<IIIII", b, pos + 8
    )
    offsets = struct.unpack_from("<" + "I" * string_count, b, pos + header_size)

    changed: list[tuple[str, str]] = []
    for rel_off in offsets:
        start = pos + strings_start + rel_off
        n_chars, len_bytes = _read_utf16_len(b, start)
        payload_start = start + len_bytes
        payload_end = payload_start + n_chars * 2
        s = bytes(b[payload_start:payload_end]).decode("utf-16le")
        if s in repl:
            ns = repl[s]
            enc = ns.encode("utf-16le")
            if len(enc) != payload_end - payload_start:
                raise PatchError(f"Encoded replacement length mismatch for {s!r}")
            b[payload_start:payload_end] = enc
            changed.append((s, ns))

    if not any(old == OLD_PKG for old, _ in changed):
        raise PatchError("Input does not look like a normal com.spotify.music APK")
    return bytes(b), changed, _unknown_manifest_strings(strings)


def patch_dex_exact_package(
    data: bytes, new_pkg: str = NEW_PKG
) -> tuple[bytes, int]:
    analysis = analyse_dex("dex", data, new_pkg)
    if analysis.error:
        raise PatchError("DEX analysis failed before patching: " + analysis.error)
    if not analysis.sort_safe:
        detail = "; ".join(analysis.neighbours) or "unknown lexical ordering"
        raise PatchError(
            "The alternate process/package string is not lexically safe in this DEX. "
            "Refusing to create an invalid APK. " + detail
        )

    old = bytes([len(OLD_PKG)]) + OLD_PKG.encode("ascii") + b"\x00"
    new = bytes([len(new_pkg)]) + new_pkg.encode("ascii") + b"\x00"
    count = data.count(old)
    if count == 0:
        return data, 0
    b = bytearray(data.replace(old, new))
    if len(b) != len(data):
        raise PatchError("DEX patch unexpectedly changed file size")
    b[12:32] = hashlib.sha1(bytes(b[32:])).digest()
    struct.pack_into("<I", b, 8, zlib.adler32(bytes(b[12:])) & 0xFFFFFFFF)
    return bytes(b), count



# ---- Spotify 8.9.76.538 BYD UI / auto-resume / branding profile helpers ----
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def read_len8(b,o):
    x=b[o]; o+=1
    if x&0x80:
        x=((x&0x7f)<<7)|b[o]; o+=1
    return x,o
def read_len16(b,o):
    x=u16(b,o); o+=2
    if x&0x8000:
        x=((x&0x7fff)<<16)|u16(b,o); o+=2
    return x,o
def enc_len8(v):
    if v<0x80: return bytes([v])
    if v<0x4000: return bytes([(v>>7)|0x80,v&0x7f])
    raise ValueError(v)
def enc_len16(v):
    if v<0x8000:return struct.pack('<H',v)
    if v<0x80000000:return struct.pack('<HH',(v>>16)|0x8000,v&0xffff)
    raise ValueError(v)

def parse_pool(data,off):
    typ,hs,sz=struct.unpack_from('<HHI',data,off)
    assert typ==1
    sc,sty,flags,strings_start,styles_start=struct.unpack_from('<IIIII',data,off+8)
    str_offs=[u32(data,off+hs+4*i) for i in range(sc)]
    style_offs=[u32(data,off+hs+4*sc+4*i) for i in range(sty)]
    arr=[]; utf8=bool(flags&0x100)
    for oo in str_offs:
        p=off+strings_start+oo
        if utf8:
            _,p=read_len8(data,p); bl,p=read_len8(data,p); arr.append(data[p:p+bl].decode('utf-8','replace'))
        else:
            l,p=read_len16(data,p); arr.append(data[p:p+2*l].decode('utf-16le','replace'))
    style_data=b'' if not styles_start else bytes(data[off+styles_start:off+sz])
    return {'strings':arr,'size':sz,'flags':flags,'style_count':sty,'style_offsets':style_offs,'style_data':style_data,'header_size':hs}

def build_pool(strings, meta):
    flags=meta['flags']; sty=meta['style_count']; style_offsets=meta['style_offsets']; style_data=meta['style_data']; utf8=bool(flags&0x100)
    blob=bytearray(); offsets=[]
    for s in strings:
        offsets.append(len(blob))
        if utf8:
            bs=s.encode('utf-8'); u16len=len(s.encode('utf-16le'))//2
            blob+=enc_len8(u16len)+enc_len8(len(bs))+bs+b'\0'
        else:
            bs=s.encode('utf-16le'); blob+=enc_len16(len(bs)//2)+bs+b'\0\0'
    hs=28
    strings_start=hs+4*len(strings)+4*sty
    blob+=b'\0'*((-len(blob))&3)
    if sty:
        styles_start=strings_start+len(blob); size=styles_start+len(style_data)
    else:
        styles_start=0; size=strings_start+len(blob)
    size=(size+3)&~3
    out=bytearray(size)
    struct.pack_into('<HHI',out,0,1,hs,size)
    struct.pack_into('<IIIII',out,8,len(strings),sty,flags,strings_start,styles_start)
    for i,v in enumerate(offsets): struct.pack_into('<I',out,hs+4*i,v)
    base=hs+4*len(strings)
    for i,v in enumerate(style_offsets): struct.pack_into('<I',out,base+4*i,v)
    out[strings_start:strings_start+len(blob)]=blob
    if sty: out[styles_start:styles_start+len(style_data)]=style_data
    return bytes(out)

def _map_idx(idx,mapping):
    return idx if idx==0xffffffff else mapping.get(idx,idx)

def _attr_res_id(name_idx,resmap):
    return resmap[name_idx] if 0 <= name_idx < len(resmap) else 0xffffffff

def patch_rhs_layout(data, new_pkg: str = NEW_PKG):
    root_hs=u16(data,2); assert root_hs==8
    pool_off=root_hs; meta=parse_pool(data,pool_off); old=meta['strings']
    ltr_class = new_pkg + '.LtrFrameLayout'
    if 'layoutDirection' in old or ltr_class in old:
        raise RuntimeError('layout already RHS-patched')
    if 'FrameLayout' not in old: raise RuntimeError('FrameLayout not found')
    insert=8
    new=list(old); new.insert(insert,'layoutDirection')
    # old index mapping after insertion
    mapping={i:(i+1 if i>=insert else i) for i in range(len(old))}
    frame_old=old.index('FrameLayout'); frame_new=mapping[frame_old]
    new[frame_new]=ltr_class
    newpool=build_pool(new,meta)

    o=pool_off+meta['size']
    # resource map
    typ,hs,sz=struct.unpack_from('<HHI',data,o); assert typ==0x0180
    vals=[u32(data,o+hs+4*i) for i in range((sz-hs)//4)]
    assert len(vals)==19
    vals.insert(insert,0x010103b2)
    rm=bytearray(hs+4*len(vals)); rm[:hs]=data[o:o+hs]
    struct.pack_into('<I',rm,4,len(rm))
    for i,v in enumerate(vals): struct.pack_into('<I',rm,hs+4*i,v)
    o+=sz

    chunks=[]
    # track direct MainLayout context via depth after start/end
    depth=0
    while o<len(data):
        typ,hs,sz=struct.unpack_from('<HHI',data,o)
        c=bytearray(data[o:o+sz])
        if typ in (0x0100,0x0101):
            # prefix, uri at 16,20
            for q in (16,20): struct.pack_into('<I',c,q,_map_idx(u32(c,q),mapping))
        elif typ==0x0102:
            # start element
            for q in (16,20): struct.pack_into('<I',c,q,_map_idx(u32(c,q),mapping))
            attrStart,attrSize,attrCount,idIndex,classIndex,styleIndex=struct.unpack_from('<HHHHHH',c,24)
            ap=16+attrStart
            for i in range(attrCount):
                aoff=ap+i*attrSize
                for q in (0,4,8): struct.pack_into('<I',c,aoff+q,_map_idx(u32(c,aoff+q),mapping))
                dtype=c[aoff+15]
                if dtype==3:
                    struct.pack_into('<I',c,aoff+16,_map_idx(u32(c,aoff+16),mapping))
            tag=new[u32(c,20)]
            # read id attr if any
            idval=None
            attrs=[]
            for i in range(attrCount):
                aoff=ap+i*attrSize; namei=u32(c,aoff+4); name=new[namei]
                dtype=c[aoff+15]; dval=u32(c,aoff+16); raw=u32(c,aoff+8)
                attrs.append((name,aoff,namei,dtype,dval,raw))
                if name=='id': idval=dval
            need_dir=None
            if tag=='com.spotify.musicappplatform.main.MainLayout': need_dir=1
            elif tag in (ltr_class,'androidx.coordinatorlayout.widget.CoordinatorLayout','com.spotify.encoremobile.tooltip.TooltipContainer'):
                need_dir=2
            if tag=='androidx.constraintlayout.widget.Guideline' and idval==0x7f0b12a3:
                for name,aoff,namei,dtype,dval,raw in attrs:
                    if name=='layout_constraintGuide_percent':
                        assert dtype==4 and dval==0x3e800000,hex(dval)
                        struct.pack_into('<I',c,aoff+16,0x3ea3d70a)
            if need_dir is not None:
                ld_idx=insert
                # create attr using android ns URI. Find existing android namespace idx from an android attr.
                android_ns=None
                for name,aoff,namei,dtype,dval,raw in attrs:
                    rid=_attr_res_id(namei,vals)
                    if (rid>>24)==0x01:
                        android_ns=u32(c,aoff); break
                if android_ns is None:
                    # known URI in pool
                    android_ns=new.index('http://schemas.android.com/apk/res/android')
                attr=struct.pack('<IIIHBBI',android_ns,ld_idx,0xffffffff,8,0,0x10,need_dir)
                # insert sorted by resource id 0x010103b2
                insert_i=attrCount
                for i,(name,aoff,namei,dtype,dval,raw) in enumerate(attrs):
                    if _attr_res_id(namei,vals)>0x010103b2:
                        insert_i=i; break
                insert_pos=ap+insert_i*attrSize
                c=c[:insert_pos]+attr+c[insert_pos:]
                struct.pack_into('<I',c,4,sz+attrSize)
                struct.pack_into('<H',c,28,attrCount+1)
        elif typ==0x0103:
            for q in (16,20): struct.pack_into('<I',c,q,_map_idx(u32(c,q),mapping))
        elif typ==0x0104:
            struct.pack_into('<I',c,16,_map_idx(u32(c,16),mapping))
            if c[23]==3: struct.pack_into('<I',c,24,_map_idx(u32(c,24),mapping))
        chunks.append(bytes(c)); o+=sz
    out=bytearray(data[:root_hs])+newpool+bytes(rm)+b''.join(chunks)
    struct.pack_into('<I',out,4,len(out))
    return bytes(out)

def replace_xml_strings(data,replacements):
    root_hs=u16(data,2); meta=parse_pool(data,root_hs); old=meta['strings']; new=list(old); changed=[]
    for i,s in enumerate(old):
        if s in replacements:
            new[i]=replacements[s]; changed.append((i,s,new[i]))
    missing=[s for s in replacements if s not in old]
    if missing: raise RuntimeError('missing strings '+repr(missing))
    pool=build_pool(new,meta)
    tail=data[root_hs+meta['size']:]
    out=bytearray(data[:root_hs])+pool+tail
    struct.pack_into('<I',out,4,len(out))
    return bytes(out),changed

def patch_autoresume_manifest(data, new_pkg: str = NEW_PKG):
    resume_service = new_pkg + '.AutoResumeService'
    repl={
      'android.media.MediaRoute2ProviderService':'byd.intent.action.RESTORE_PLAYBACK',
      'com.spotify.connect.mediarouteprovider.SpotifyMediaRouteProviderService':resume_service,
    }
    data,_=replace_xml_strings(data,repl)
    meta=parse_pool(data,u16(data,2)); ss=meta['strings']; o=u16(data,2)+meta['size']
    # resource map
    t,h,s=struct.unpack_from('<HHI',data,o); assert t==0x180
    resmap=[u32(data,o+h+4*i) for i in range((s-h)//4)]
    chunks=[data[o:o+s]]; o+=s; found=False
    while o<len(data):
        t,h,s=struct.unpack_from('<HHI',data,o); c=bytearray(data[o:o+s])
        if t==0x0102:
            tag=ss[u32(c,20)]
            attrStart,attrSize,attrCount,*_=struct.unpack_from('<HHHHHH',c,24); ap=16+attrStart
            attrs=[]
            for i in range(attrCount):
                ao=ap+i*attrSize; namei=u32(c,ao+4); raw=u32(c,ao+8); dtype=c[ao+15]; dval=u32(c,ao+16)
                rawval=ss[raw] if raw!=0xffffffff else None
                val=rawval if rawval is not None else (ss[dval] if dtype==3 else dval)
                attrs.append((ss[namei],ao,namei,dtype,dval,raw,val))
            if tag=='service' and any(n=='name' and v==resume_service for n,ao,ni,dt,dv,r,v in attrs):
                found=True
                for n,ao,ni,dt,dv,r,v in attrs:
                    if n=='enabled':
                        assert dt==0x12 and dv==0
                        struct.pack_into('<I',c,ao+16,0xffffffff)
                fg_idx=ss.index('foregroundServiceType')
                android_ns=ss.index('http://schemas.android.com/apk/res/android')
                attr=struct.pack('<IIIHBBI',android_ns,fg_idx,0xffffffff,8,0,0x11,2)
                # insert sorted by mapped resource id
                target_rid=resmap[fg_idx]
                ins=attrCount
                for i,(n,ao,ni,dt,dv,r,v) in enumerate(attrs):
                    rid=resmap[ni] if ni<len(resmap) else 0xffffffff
                    if rid>target_rid: ins=i; break
                pos=ap+ins*attrSize
                c=c[:pos]+attr+c[pos:]
                struct.pack_into('<I',c,4,s+attrSize); struct.pack_into('<H',c,28,attrCount+1)
        chunks.append(bytes(c)); o+=s
    if not found: raise RuntimeError('restore service slot not found')
    out=bytearray(data[:u16(data,2)+meta['size']])+b''.join(chunks)
    struct.pack_into('<I',out,4,len(out))
    return bytes(out)

# ARSC helpers

def package_pools(data,pkg_off):
    typeStrings=u32(data,pkg_off+268); keyStrings=u32(data,pkg_off+276)
    return parse_pool(data,pkg_off+typeStrings)['strings'], parse_pool(data,pkg_off+keyStrings)['strings']

def iter_resource_values(data,rid,complex_items=False):
    root_hs=u16(data,2); gp=parse_pool(data,root_hs); o=root_hs+gp['size']
    pkgid=(rid>>24)&0xff; typeid=(rid>>16)&0xff; entryid=rid&0xffff
    while o<len(data):
        ctyp,chs,csz=struct.unpack_from('<HHI',data,o)
        if ctyp==0x0200 and u32(data,o+8)==pkgid:
            tnames,knames=package_pools(data,o); p=o+chs; end=o+csz
            while p<end:
                t,h,s=struct.unpack_from('<HHI',data,p)
                if t==0x0201 and data[p+8]==typeid:
                    entryCount=u32(data,p+12); entriesStart=u32(data,p+16)
                    if entryid<entryCount:
                        eoff=u32(data,p+h+4*entryid)
                        if eoff!=0xffffffff:
                            ep=p+entriesStart+eoff; esize=u16(data,ep); flags=u16(data,ep+2); keyidx=u32(data,ep+4)
                            if flags&1:
                                if complex_items:
                                    cnt=u32(data,ep+12); q=ep+16
                                    for j in range(cnt):
                                        name=u32(data,q); vp=q+4; yield {'pos':vp+4,'dtype':data[vp+3],'dval':u32(data,vp+4),'map_name':name,'key':knames[keyidx],'type':tnames[typeid-1]}; q+=12
                            elif not complex_items:
                                vp=ep+esize; yield {'pos':vp+4,'dtype':data[vp+3],'dval':u32(data,vp+4),'key':knames[keyidx],'type':tnames[typeid-1]}
                p+=s
            return
        o+=csz

def patch_ui_v9_resources(data):
    b=bytearray(data); changes=[]
    simple={
      0x7f0704c6:{0x00000c01:0x00000f01},
      0x7f0704c9:{0x00003801:0x00004601},
      0x7f070526:{0x00004001:0x00005001},
      0x7f070529:{0x00003001:0x00003c01},
      0x7f07053b:{0x00001801:0x00001e01},
      0x7f070811:{0x00003801:0x00004601,0x00002701:0x00003a01},
      0x7f070908:{0x00004801:0x00005301},
      0x7f070a61:{0x00003001:0x00003c01},
      0x7f070a64:{0x00003001:0x00003c01},
      0x7f07006d:{0x00008601:0x00002c01,0x00009001:0x00002f01,0x0000b401:0x00003b01},
      0x7f0703bd:{0x00004001:0x00003001,0x0000a001:0x00003501},
      0x7f0703be:{0x00004001:0x00003001,0x0000a001:0x00003501},
      0x7f070484:{0x00004001:0x00003001,0x0000a001:0x00003501},
      0x7f070486:{0x00004001:0x00003001,0x0000a001:0x00003501},
      0x7f070a59:{0x00000e02:0x00001402,0x00001002:0x00001602,0x00001202:0x00001902},
      0x7f070a5a:{0x00001202:0x00001b02,0x00001402:0x00001e02,0x00001602:0x00002202},
    }
    for rid,m in simple.items():
        for v in list(iter_resource_values(b,rid,False)):
            if v['dtype']==5 and v['dval'] in m:
                nv=m[v['dval']]; struct.pack_into('<I',b,v['pos'],nv); changes.append((rid,v['dval'],nv))
    styles={
      0x7f140367:{0x00000902:0x00000d02},
      0x7f140369:{0x00001002:0x00001702},
      0x7f14036a:{0x00001002:0x00001702},
      0x7f14036b:{0x00000d02:0x00001202},
      0x7f14036c:{0x00000d02:0x00001202},
      0x7f14036f:{0x00000b02:0x00001002},
      0x7f140372:{0x00000b02:0x00001002},
      0x7f140375:{0x00000a02:0x00000e02},
      0x7f140378:{0x00001802:0x00002202},
      0x7f14037a:{0x00001402:0x00001d02},
    }
    for rid,m in styles.items():
        for v in list(iter_resource_values(b,rid,True)):
            if v['map_name']==0x01010095 and v['dtype']==5 and v['dval'] in m:
                nv=m[v['dval']]; struct.pack_into('<I',b,v['pos'],nv); changes.append((rid,v['dval'],nv))
    if len(changes)!=40: raise RuntimeError(f'expected 40 v9 UI changes, got {len(changes)}')
    return bytes(b),changes

FG_RID = ADAPTIVE_FOREGROUND_RID
OLD_FG_PATH = OLD_ADAPTIVE_FOREGROUND_PATH
NEW_FG_PATH = NEW_ADAPTIVE_FOREGROUND_PATH
NEW_LABEL = NEW_APP_LABEL
DENSITY_ICONS = DENSITY_ICON_PATHS

def rebuild_global_pool(data,extra_strings):
    ROOT_HS=u16(data,2); pool_off=ROOT_HS; p=parse_pool(data,pool_off); strings=list(p['strings']); idxs={}
    for s in extra_strings:
        if s in strings: idx=strings.index(s)
        else: idx=len(strings); strings.append(s)
        idxs[s]=idx
    pool=build_pool(strings,p); oldsz=p['size']
    out=bytearray(data[:pool_off])+pool+data[pool_off+oldsz:]; struct.pack_into('<I',out,4,len(out)); return out,idxs

def find_value_positions(data,rid): return list(iter_resource_values(data,rid,False))

def add_plus(im):
    im=im.convert('RGBA'); w,h=im.size; d=ImageDraw.Draw(im); cx=w//2; cy=int(round(h*0.79)); stroke=max(2,round(w*0.045)); half=max(3,round(w*0.085)); r=max(1,stroke//2)
    d.rounded_rectangle([cx-half,cy-r,cx+half,cy+r],radius=r,fill=(0,0,0,255)); d.rounded_rectangle([cx-r,cy-half,cx+r,cy+half],radius=r,fill=(0,0,0,255)); return im


def shift_hue(im, degrees: int):
    """Rotate icon hue while preserving alpha, saturation and brightness."""
    degrees = normalise_hue(degrees)
    rgba = im.convert('RGBA')
    if degrees == 0:
        return rgba
    alpha = rgba.getchannel('A')
    hsv = rgba.convert('RGB').convert('HSV')
    h, s, v = hsv.split()
    delta = int(round(degrees * 255 / 360.0)) % 256
    h = h.point([(i + delta) % 256 for i in range(256)])
    rgb = Image.merge('HSV', (h, s, v)).convert('RGB')
    out = rgb.convert('RGBA')
    out.putalpha(alpha)
    return out


def load_preview_icon_from_apk(apk_path: str) -> Image.Image | None:
    """Load the highest-density launcher icon available from a selected APK."""
    apk_path = (apk_path or "").strip()
    if not apk_path or not os.path.isfile(apk_path):
        return None

    preferred = list(reversed(DENSITY_ICON_PATHS))
    try:
        with zipfile.ZipFile(apk_path, "r") as zf:
            for path in preferred:
                try:
                    data = zf.read(path)
                except KeyError:
                    continue
                with Image.open(io.BytesIO(data)) as im:
                    return im.convert("RGBA")
    except (OSError, zipfile.BadZipFile):
        return None
    return None


def build_logo_preview_image(source_icon: Image.Image | None, hue: int, size: int = 112) -> Image.Image:
    """Render the same + mark and hue rotation used by the APK branding patch."""
    hue = normalise_hue(hue)
    canvas = Image.new("RGBA", (size, size), (245, 245, 245, 255))
    if source_icon is None:
        return canvas

    preview = shift_hue(add_plus(source_icon.copy()), hue)
    max_icon = max(32, size - 18)
    preview.thumbnail((max_icon, max_icon), Image.Resampling.LANCZOS)
    x = (size - preview.width) // 2
    y = (size - preview.height) // 2
    canvas.alpha_composite(preview, (x, y))
    return canvas


def patch_branding(resources, source_icons, app_label: str = NEW_APP_LABEL, icon_hue: int = 0):
    app_label = validate_app_label(app_label)
    icon_hue = normalise_hue(icon_hue)
    arsc=bytearray(resources); original=parse_pool(arsc,u16(arsc,2)); tmp=list(original['strings']); idxmap={}
    for s in [app_label,NEW_FG_PATH]:
        if s in tmp: idx=tmp.index(s)
        else: idx=len(tmp);tmp.append(s)
        idxmap[s]=idx
    for rid,new_idx,expect_key in [(APP_NAME_RID,idxmap[app_label],'app_name'),(FG_RID,idxmap[NEW_FG_PATH],'ic_launcher_renaissance_foreground')]:
        vals=find_value_positions(arsc,rid)
        if not vals: raise RuntimeError(f'RID {rid:#x} not found')
        for v in vals:
            if v['key']!=expect_key or v['dtype']!=3: raise RuntimeError((rid,v))
            struct.pack_into('<I',arsc,v['pos'],new_idx)
    arsc,idxs=rebuild_global_pool(arsc,[app_label,NEW_FG_PATH])
    icon_repl={}
    for path,bb in source_icons.items():
        im=Image.open(io.BytesIO(bb)); out=shift_hue(add_plus(im), icon_hue); buf=io.BytesIO(); out.save(buf,'WEBP',lossless=True,quality=100,method=6); icon_repl[path]=buf.getvalue()
    base=shift_hue(add_plus(Image.open(io.BytesIO(source_icons['res/mipmap-xxxhdpi-v4/ic_launcher_renaissance.webp']))), icon_hue); base=base.resize((240,240),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(432,432),(0,0,0,0)); canvas.alpha_composite(base,((432-240)//2,(432-240)//2)); buf=io.BytesIO(); canvas.save(buf,'PNG',optimize=True)
    return bytes(arsc),icon_repl,buf.getvalue()


def retarget_helper_dex(data: bytes, new_pkg: str) -> bytes:
    """Retarget only our injected helper classes; helper behavior is unchanged."""
    if new_pkg == NEW_PKG:
        return data
    if len(new_pkg) != len(NEW_PKG):
        raise PatchError("Helper package replacement must preserve DEX string length")
    old_slash = NEW_PKG.replace('.', '/').encode('ascii')
    new_slash = new_pkg.replace('.', '/').encode('ascii')
    old_dot = NEW_PKG.encode('ascii')
    new_dot = new_pkg.encode('ascii')
    b = bytearray(data.replace(old_slash, new_slash).replace(old_dot, new_dot))
    if len(b) != len(data):
        raise PatchError("Helper DEX retarget unexpectedly changed file size")
    b[12:32] = hashlib.sha1(bytes(b[32:])).digest()
    struct.pack_into('<I', b, 8, zlib.adler32(bytes(b[12:])) & 0xFFFFFFFF)
    return bytes(b)


def is_v1_signature_metadata(name: str) -> bool:
    upper = name.upper()
    return upper == "META-INF/MANIFEST.MF" or bool(SIGNATURE_RE.fullmatch(name))


def _copy_zipinfo(info: zipfile.ZipInfo) -> zipfile.ZipInfo:
    ni = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
    ni.compress_type = info.compress_type
    ni.comment = info.comment
    ni.extra = info.extra
    ni.internal_attr = info.internal_attr
    ni.external_attr = info.external_attr
    ni.create_system = info.create_system
    ni.create_version = info.create_version
    ni.extract_version = info.extract_version
    ni.flag_bits = info.flag_bits
    return ni


def _add_alignment_extra(info: zipfile.ZipInfo, current_offset: int, alignment: int = 4) -> None:
    name_len = len(info.filename.encode("utf-8"))
    base = current_offset + 30 + name_len + len(info.extra)
    needed = (-base) % alignment
    if needed:
        # Total new extra bytes are 4 + needed; 4 is itself aligned.
        info.extra += struct.pack("<HH", 0xD935, needed) + (b"\x00" * needed)


def verify_alignment(path: Path, alignment: int = 4) -> None:
    with path.open("rb") as f, zipfile.ZipFile(f, "r") as z:
        for info in z.infolist():
            if info.compress_type != zipfile.ZIP_STORED:
                continue
            f.seek(info.header_offset)
            hdr = f.read(30)
            if len(hdr) != 30 or hdr[:4] != b"PK\x03\x04":
                raise PatchError(f"Invalid local ZIP header for {info.filename}")
            name_len, extra_len = struct.unpack_from("<HH", hdr, 26)
            data_off = info.header_offset + 30 + name_len + extra_len
            if data_off % alignment:
                raise PatchError(
                    f"Uncompressed entry is not {alignment}-byte aligned: {info.filename} @ {data_off}"
                )


def _manifest_version_info(data: bytes) -> tuple[str | None, int | None]:
    """Read versionName/versionCode from the binary manifest root element."""
    root_hs = u16(data, 2)
    meta = parse_pool(data, root_hs)
    strings = meta["strings"]
    o = root_hs + meta["size"]
    if o + 8 <= len(data) and u16(data, o) == 0x0180:
        o += u32(data, o + 4)
    while o + 8 <= len(data):
        typ, _hs, sz = struct.unpack_from("<HHI", data, o)
        if typ == 0x0102:
            tag = strings[u32(data, o + 20)]
            if tag == "manifest":
                attr_start, attr_size, attr_count, *_ = struct.unpack_from("<HHHHHH", data, o + 24)
                ap = o + 16 + attr_start
                version_name: str | None = None
                version_code: int | None = None
                for i in range(attr_count):
                    ao = ap + i * attr_size
                    name_idx = u32(data, ao + 4)
                    raw_idx = u32(data, ao + 8)
                    dtype = data[ao + 15]
                    dval = u32(data, ao + 16)
                    name = strings[name_idx]
                    if name == "versionName":
                        if raw_idx != 0xFFFFFFFF:
                            version_name = strings[raw_idx]
                        elif dtype == 3 and dval < len(strings):
                            version_name = strings[dval]
                    elif name == "versionCode":
                        version_code = int(dval)
                return version_name, version_code
        o += sz
    return None, None


def _profile_resource_sanity(resources: bytes) -> None:
    """Fail if the resource table no longer matches the proven 8.9.76 profile."""
    # This performs the same structural lookup as the real patch, on a temporary
    # copy. The exact expected 40 changes are a strong compatibility fingerprint.
    patch_ui_v9_resources(resources)
    for rid, expected_key in (
        (APP_NAME_RID, "app_name"),
        (ADAPTIVE_FOREGROUND_RID, "ic_launcher_renaissance_foreground"),
    ):
        vals = list(iter_resource_values(resources, rid, False))
        if not vals or any(v["key"] != expected_key for v in vals):
            raise PatchError(f"Required Spotify 8.9 resource {expected_key} was not found as expected")


def analyse_apk(
    input_path: str | Path,
    log: Callable[[str], None] | None = None,
    target_package: str = NEW_PKG,
) -> ApkAnalysis:
    log = log or (lambda _s: None)
    src = Path(input_path)
    if not src.is_file():
        raise PatchError(f"Input APK not found: {src}")
    try:
        zin = zipfile.ZipFile(src, "r")
    except zipfile.BadZipFile as e:
        raise PatchError("The selected file is not a valid APK/ZIP archive") from e

    warnings: list[str] = []
    ui_profile_ok = False
    wide_layout_sha: str | None = None
    with zin:
        names = {i.filename for i in zin.infolist()}
        for required in ("AndroidManifest.xml", "resources.arsc", "classes.dex", WIDE_LAYOUT_PATH):
            if required not in names:
                raise PatchError(f"Input is missing required APK entry: {required}")

        manifest = zin.read("AndroidManifest.xml")
        strings, has_pkg = _scan_binary_manifest(manifest)
        if not has_pkg:
            raise PatchError("Selected APK is not an original com.spotify.music package")
        spotify_version, spotify_version_code = _manifest_version_info(manifest)
        if spotify_version != SUPPORTED_SPOTIFY_VERSION or spotify_version_code != SUPPORTED_SPOTIFY_VERSION_CODE:
            warnings.append(
                f"This patch profile supports Spotify {SUPPORTED_SPOTIFY_VERSION} "
                f"(versionCode {SUPPORTED_SPOTIFY_VERSION_CODE}) only; selected APK is "
                f"{spotify_version or 'unknown'} ({spotify_version_code if spotify_version_code is not None else 'unknown'})."
            )

        repl = _manifest_replacements(target_package)
        manifest_patch_count = sum(1 for x in strings if x in repl)
        unknown_manifest = _unknown_manifest_strings(strings)
        if unknown_manifest:
            warnings.append(
                "New package-scoped manifest strings were detected and will be left unchanged for safety."
            )

        restore_manifest_ok = (
            "com.spotify.connect.mediarouteprovider.SpotifyMediaRouteProviderService" in strings
            and "android.media.MediaRoute2ProviderService" in strings
            and "foregroundServiceType" in strings
        )
        if not restore_manifest_ok:
            warnings.append("The known MediaRoute service slot required for BYD auto-resume was not found.")

        resources = zin.read("resources.arsc")
        resource_matches: dict[str, int] = {}
        for old in _resource_replacements(target_package):
            c = resources.count(old)
            if c:
                resource_matches[old.decode("ascii")] = c
        if not resource_matches:
            warnings.append("Known media-api provider authority was not found.")

        try:
            _profile_resource_sanity(resources)
            ui_profile_ok = True
        except Exception as e:
            warnings.append("Spotify 8.9 BYD UI resource profile mismatch: " + str(e))

        wide_layout = zin.read(WIDE_LAYOUT_PATH)
        wide_layout_sha = hashlib.sha256(wide_layout).hexdigest()
        if wide_layout_sha != WIDE_LAYOUT_BASE_SHA256:
            warnings.append("The wide-screen adaptive layout does not match the proven Spotify 8.9.76.538 profile.")

        missing_icons = [p for p in DENSITY_ICON_PATHS + [OLD_ADAPTIVE_FOREGROUND_PATH] if p not in names]
        if missing_icons:
            warnings.append("Launcher branding resources are missing: " + ", ".join(missing_icons))

        dex_entries = sorted(
            (i.filename for i in zin.infolist() if re.fullmatch(r"classes(?:\d+)?\.dex", i.filename)),
            key=lambda n: (len(n), n),
        )
        dex_results = [analyse_dex(name, zin.read(name), target_package) for name in dex_entries]
        if any(d.error for d in dex_results):
            warnings.append("At least one DEX file could not be structurally analysed.")
        if not any(d.exact_package_occurrences for d in dex_results):
            warnings.append("No exact Spotify process/package string was found in DEX files.")
        if any(not d.sort_safe for d in dex_results):
            warnings.append("DEX lexical ordering would be unsafe with the selected alternate package name.")
        if len(dex_entries) != 7 or "classes8.dex" in names or "classes9.dex" in names:
            warnings.append("Expected the stock Spotify 8.9 seven-DEX layout (classes.dex through classes7.dex).")

        services = sorted(i.filename for i in zin.infolist() if i.filename.startswith("META-INF/services/"))
        abis = sorted(
            {
                parts[1]
                for i in zin.infolist()
                if (parts := i.filename.split("/")) and len(parts) >= 3 and parts[0] == "lib"
            }
        )

    compatible = (
        spotify_version == SUPPORTED_SPOTIFY_VERSION
        and spotify_version_code == SUPPORTED_SPOTIFY_VERSION_CODE
        and manifest_patch_count > 0
        and restore_manifest_ok
        and bool(resource_matches)
        and ui_profile_ok
        and wide_layout_sha == WIDE_LAYOUT_BASE_SHA256
        and len(dex_results) == 7
        and any(d.exact_package_occurrences for d in dex_results)
        and all(d.sort_safe and not d.error for d in dex_results)
        and not missing_icons
    )
    result = ApkAnalysis(
        input_path=src,
        input_sha256=sha256_file(src),
        size_bytes=src.stat().st_size,
        spotify_version=spotify_version,
        spotify_version_code=spotify_version_code,
        profile_name=f"Spotify {SUPPORTED_SPOTIFY_VERSION} / BYD v9-v14",
        wide_layout_sha256=wide_layout_sha,
        dex_count=len(dex_results),
        native_abis=abis,
        services=services,
        manifest_patch_count=manifest_patch_count,
        unknown_manifest_strings=unknown_manifest,
        resource_matches=resource_matches,
        dex=dex_results,
        target_package=target_package,
        compatible=compatible,
        warnings=warnings,
    )
    log(
        f"APK analysis: {'SUPPORTED' if compatible else 'NOT SUPPORTED'} — "
        f"Spotify {spotify_version or 'unknown'}"
    )
    return result


def _write_added_deflated(zout: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0x01800000
    zout.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def patch_apk(
    input_path: str | Path,
    output_path: str | Path,
    panel_side: str = PANEL_LEFT,
    log: Callable[[str], None] | None = None,
    instance: str = INSTANCE_PRIMARY,
    app_label: str | None = None,
    icon_hue: int | float | None = None,
) -> PatchReport:
    log = log or (lambda _s: None)
    panel_side = panel_side.lower().strip()
    if panel_side not in (PANEL_LEFT, PANEL_RIGHT):
        raise PatchError("panel_side must be 'left' or 'right'")

    cfg = get_instance_config(instance)
    instance = instance.lower().strip()
    target_package = cfg["package"]
    app_label = validate_app_label(app_label if app_label is not None else cfg["label"])
    icon_hue = normalise_hue(cfg["hue"] if icon_hue is None else icon_hue)

    src = Path(input_path)
    out = Path(output_path)
    if not src.is_file():
        raise PatchError(f"Input APK not found: {src}")
    if src.resolve() == out.resolve():
        raise PatchError("Input and output paths must be different")
    out.parent.mkdir(parents=True, exist_ok=True)

    analysis = analyse_apk(src, log, target_package)
    if not analysis.compatible:
        raise PatchError(
            f"Only the proven Spotify {SUPPORTED_SPOTIFY_VERSION} APK profile is supported by v{APP_VERSION}. "
            "No output was created."
        )

    input_sha = analysis.input_sha256
    log(f"Input SHA-256: {input_sha}")
    log(f"App instance: {cfg['title']} — {target_package}")
    log(f"Display name: {app_label}")
    log(f"Launcher icon hue shift: {icon_hue}°")
    log("Panel profile: " + ("LEFT / LHD (v9 layout)" if panel_side == PANEL_LEFT else "RIGHT / RHD (v14 layout)"))

    manifest_changes: list[tuple[str, str]] = []
    dex_changes: dict[str, int] = {}
    resource_changes: dict[str, int] = {}
    removed_signatures: list[str] = []
    warnings = list(analysis.warnings)
    ui_changes: list[tuple[int, int, int]] = []

    try:
        with zipfile.ZipFile(src, "r") as zin:
            names = {i.filename for i in zin.infolist()}
            patched_manifest, manifest_changes, unknown_manifest = patch_binary_manifest(
                zin.read("AndroidManifest.xml"), target_package
            )
            if unknown_manifest:
                warnings.append(
                    "Unrecognised package-scoped manifest strings were left unchanged: "
                    + ", ".join(unknown_manifest)
                )
            patched_manifest = patch_autoresume_manifest(patched_manifest, target_package)
            log("BYD RESTORE_PLAYBACK auto-resume service injected.")

            resources = zin.read("resources.arsc")
            for old, new_value in _resource_replacements(target_package).items():
                if len(old) != len(new_value):
                    raise AssertionError("resources.arsc replacement length mismatch")
                count = resources.count(old)
                if count:
                    resources = resources.replace(old, new_value)
                    resource_changes[old.decode("ascii")] = count

            resources, ui_changes = patch_ui_v9_resources(resources)
            log(f"Applied proven v9 compact/larger-text resource profile ({len(ui_changes)} resource values).")

            source_icons = {p: zin.read(p) for p in DENSITY_ICON_PATHS}
            resources, icon_replacements, adaptive_png = patch_branding(
                resources, source_icons, app_label, icon_hue
            )
            log(f"Applied {app_label!r} app label, '+' launcher mark and {icon_hue}° hue shift.")

            wide_layout = zin.read(WIDE_LAYOUT_PATH)
            if panel_side == PANEL_RIGHT:
                wide_layout = patch_rhs_layout(wide_layout, target_package)
                log("Applied proven v14 right-side panel transformation with LTR content containers.")

            src_services = {
                i.filename: hashlib.sha256(zin.read(i.filename)).hexdigest()
                for i in zin.infolist()
                if i.filename.startswith("META-INF/services/")
            }

            ltr_dex = retarget_helper_dex(base64.b64decode(LTR_FRAME_DEX_B64), target_package)
            auto_dex = retarget_helper_dex(base64.b64decode(AUTO_RESUME_DEX_B64), target_package)
            inject_dex: list[tuple[str, bytes]]
            if panel_side == PANEL_RIGHT:
                inject_dex = [("classes8.dex", ltr_dex), ("classes9.dex", auto_dex)]
            else:
                inject_dex = [("classes8.dex", auto_dex)]
            if any(name in names for name, _ in inject_dex):
                raise PatchError("Input already contains a DEX slot reserved by the BYD patch profile")

            with zipfile.ZipFile(out, "w", allowZip64=True) as zout:
                for info in zin.infolist():
                    name = info.filename
                    if is_v1_signature_metadata(name):
                        removed_signatures.append(name)
                        continue
                    if name == OLD_ADAPTIVE_FOREGROUND_PATH:
                        # resources.arsc now points to our PNG foreground.
                        continue

                    if name == "AndroidManifest.xml":
                        payload = patched_manifest
                    elif name == "resources.arsc":
                        payload = resources
                    elif name == WIDE_LAYOUT_PATH:
                        payload = wide_layout
                    elif name in icon_replacements:
                        payload = icon_replacements[name]
                    else:
                        payload = zin.read(name)
                        if re.fullmatch(r"classes(?:\d+)?\.dex", name):
                            payload, count = patch_dex_exact_package(payload, target_package)
                            if count:
                                dex_changes[name] = count

                    ni = _copy_zipinfo(info)
                    if ni.compress_type == zipfile.ZIP_STORED:
                        current = zout.fp.tell() if zout.fp is not None else 0
                        _add_alignment_extra(ni, current, 4)
                    zout.writestr(ni, payload, compress_type=ni.compress_type, compresslevel=6)

                _write_added_deflated(zout, NEW_ADAPTIVE_FOREGROUND_PATH, adaptive_png)
                for dex_name, dex_payload in inject_dex:
                    _write_added_deflated(zout, dex_name, dex_payload)
    except Exception:
        try:
            out.unlink(missing_ok=True)
        except Exception:
            pass
        raise

    if not dex_changes:
        out.unlink(missing_ok=True)
        raise PatchError("No exact com.spotify.music DEX package/process marker was patched")

    verify_alignment(out, 4)
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(out, "r") as zout:
        out_services = {
            i.filename: hashlib.sha256(zout.read(i.filename)).hexdigest()
            for i in zout.infolist()
            if i.filename.startswith("META-INF/services/")
        }
        if src_services != out_services:
            out.unlink(missing_ok=True)
            raise PatchError("META-INF/services runtime files were not preserved exactly")

        for name in dex_changes:
            d = zout.read(name)
            if d[12:32] != hashlib.sha1(d[32:]).digest():
                raise PatchError(f"DEX SHA-1 signature validation failed: {name}")
            if struct.unpack_from("<I", d, 8)[0] != (zlib.adler32(d[12:]) & 0xFFFFFFFF):
                raise PatchError(f"DEX Adler32 validation failed: {name}")
            old_exact = bytes([len(OLD_PKG)]) + OLD_PKG.encode() + b"\x00"
            if old_exact in d:
                raise PatchError(f"Old exact package/process string remains in {name}")

        helper_pkg_bytes = target_package.replace('.', '/').encode('ascii')
        for helper_name, _ in inject_dex:
            d = zout.read(helper_name)
            if d[12:32] != hashlib.sha1(d[32:]).digest():
                raise PatchError(f"Injected helper DEX SHA-1 validation failed: {helper_name}")
            if struct.unpack_from("<I", d, 8)[0] != (zlib.adler32(d[12:]) & 0xFFFFFFFF):
                raise PatchError(f"Injected helper DEX Adler32 validation failed: {helper_name}")
            if helper_pkg_bytes not in d:
                raise PatchError(f"Injected helper DEX package retarget failed: {helper_name}")

        out_manifest_strings, _ = _scan_binary_manifest(zout.read("AndroidManifest.xml"))
        if target_package + ".AutoResumeService" not in out_manifest_strings:
            raise PatchError("Auto-resume service manifest verification failed")
        if "byd.intent.action.RESTORE_PLAYBACK" not in out_manifest_strings:
            raise PatchError("BYD restore action manifest verification failed")

        out_resources = zout.read("resources.arsc")
        gp = parse_pool(out_resources, u16(out_resources, 2))["strings"]
        if app_label not in gp or NEW_ADAPTIVE_FOREGROUND_PATH not in gp:
            raise PatchError("App branding verification failed")

        layout_sha = hashlib.sha256(zout.read(WIDE_LAYOUT_PATH)).hexdigest()
        expected_layout = zin.read(WIDE_LAYOUT_PATH)
        if panel_side == PANEL_RIGHT:
            expected_layout = patch_rhs_layout(expected_layout, target_package)
        expected_layout_sha = hashlib.sha256(expected_layout).hexdigest()
        if layout_sha != expected_layout_sha:
            raise PatchError("Final wide-screen layout verification failed")

    output_sha = sha256_file(out)
    log(f"Unsigned patched SHA-256: {output_sha}")
    return PatchReport(
        input_path=src,
        output_path=out,
        input_sha256=input_sha,
        output_sha256=output_sha,
        panel_side=panel_side,
        instance=instance,
        package_name=target_package,
        app_label=app_label,
        icon_hue=icon_hue,
        manifest_changes=manifest_changes,
        dex_changes=dex_changes,
        resource_changes=resource_changes,
        ui_changes=len(ui_changes),
        services_preserved=len(src_services),
        removed_signatures=removed_signatures,
        warnings=warnings,
    )


def _runtime_roots() -> list[Path]:
    """Locations that may contain portable signing tools.

    PyInstaller onedir builds keep ``runtime`` and ``tools`` beside the EXE.
    One-file builds may unpack data under ``sys._MEIPASS``. Source runs also
    check the script directory so developers can drop the same folders there.
    """
    roots: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
    roots.append(Path(__file__).resolve().parent)
    # Preserve order while removing duplicates.
    out: list[Path] = []
    seen: set[str] = set()
    for r in roots:
        key = str(r).lower() if os.name == "nt" else str(r)
        if key not in seen:
            out.append(r)
            seen.add(key)
    return out


def find_bundled_signing_runtime() -> tuple[Path, Path] | None:
    """Return (java executable, apksigner.jar) from a portable distribution."""
    java_name = "java.exe" if os.name == "nt" else "java"
    for root in _runtime_roots():
        java = root / "runtime" / "bin" / java_name
        jar = root / "tools" / "apksigner.jar"
        if java.is_file() and jar.is_file():
            return java, jar
    return None


def _sdk_build_tools_roots() -> list[Path]:
    candidates: list[Path] = []
    env = os.environ
    if env.get("ANDROID_HOME"):
        candidates.append(Path(env["ANDROID_HOME"]) / "build-tools")
    if env.get("ANDROID_SDK_ROOT"):
        candidates.append(Path(env["ANDROID_SDK_ROOT"]) / "build-tools")
    if os.name == "nt":
        local = env.get("LOCALAPPDATA")
        if local:
            candidates.append(Path(local) / "Android" / "Sdk" / "build-tools")
    return candidates


def _versionish_key(p: Path) -> tuple[int, ...]:
    nums = [int(x) for x in re.findall(r"\d+", p.name)]
    return tuple(nums) if nums else (0,)


def find_sdk_apksigner_jar() -> Path | None:
    for root in _sdk_build_tools_roots():
        if root.is_dir():
            versions = sorted((p for p in root.iterdir() if p.is_dir()), key=_versionish_key, reverse=True)
            for v in versions:
                jar = v / "lib" / "apksigner.jar"
                if jar.is_file():
                    return jar
    return None


def find_apksigner() -> Path | None:
    """Find the SDK wrapper as a development fallback."""
    for root in _sdk_build_tools_roots():
        if root.is_dir():
            versions = sorted((p for p in root.iterdir() if p.is_dir()), key=_versionish_key, reverse=True)
            for v in versions:
                for name in ("apksigner.bat", "apksigner"):
                    candidate = v / name
                    if candidate.is_file():
                        return candidate
    found = shutil.which("apksigner")
    return Path(found) if found else None


def find_java_executable() -> Path | None:
    bundled = find_bundled_signing_runtime()
    if bundled:
        return bundled[0]
    if os.environ.get("JAVA_HOME"):
        p = Path(os.environ["JAVA_HOME"]) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if p.is_file():
            return p
    if os.name == "nt":
        for home in [
            Path(r"C:\Program Files\Android\Android Studio\jbr"),
            Path(r"C:\Program Files\Android\Android Studio\jre"),
        ]:
            p = home / "bin" / "java.exe"
            if p.is_file():
                return p
    found = shutil.which("java")
    return Path(found) if found else None


def find_java_home() -> Path | None:
    java = find_java_executable()
    if not java:
        return None
    # runtime/bin/java -> runtime; normal JAVA_HOME/bin/java -> JAVA_HOME
    return java.resolve().parent.parent


def find_keytool_executable() -> Path | None:
    """Find keytool for optional migration of an existing JKS keystore."""
    homes: list[Path] = []
    if os.environ.get("JAVA_HOME"):
        homes.append(Path(os.environ["JAVA_HOME"]))
    if os.name == "nt":
        homes.extend([
            Path(r"C:\Program Files\Android\Android Studio\jbr"),
            Path(r"C:\Program Files\Android\Android Studio\jre"),
        ])
    name = "keytool.exe" if os.name == "nt" else "keytool"
    for home in homes:
        candidate = home / "bin" / name
        if candidate.is_file():
            return candidate
    found = shutil.which("keytool")
    return Path(found) if found else None


@dataclass
class SigningEngine:
    kind: str
    description: str
    command_prefix: list[str]


def discover_signing_engine() -> SigningEngine | None:
    bundled = find_bundled_signing_runtime()
    if bundled:
        java, jar = bundled
        return SigningEngine("bundled", "Bundled AOSP apksigner (portable)", [str(java), "-jar", str(jar)])

    jar = find_sdk_apksigner_jar()
    java = find_java_executable()
    if jar and java:
        return SigningEngine("sdk-jar", "Android SDK apksigner.jar", [str(java), "-jar", str(jar)])

    wrapper = find_apksigner()
    if wrapper:
        return SigningEngine("sdk-wrapper", "Android SDK apksigner", [str(wrapper)])
    return None


def signing_engine_status() -> str:
    engine = discover_signing_engine()
    return engine.description if engine else "Signing runtime not found"

def app_data_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "BYDSpotifyPatcher"
    return Path.home() / ".byd-spotify-patcher"


def _load_signing_cfg() -> tuple[Path, dict] | None:
    root = app_data_dir()
    key_path = root / "signing-key.p12"
    cfg_path = root / "signing.json"
    if not key_path.exists() or not cfg_path.exists():
        return None
    try:
        cfg = json.loads(cfg_path.read_text("utf-8"))
        if "password_b64" not in cfg:
            return None
        return key_path, cfg
    except Exception:
        return None


def signing_certificate_fingerprint() -> str | None:
    loaded = _load_signing_cfg()
    if not loaded:
        return None
    key_path, cfg = loaded
    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        password = base64.b64decode(cfg["password_b64"])
        _key, cert, _cas = pkcs12.load_key_and_certificates(key_path.read_bytes(), password)
        if cert is None:
            return None
        return cert.fingerprint(hashlib_sha256_adapter()).hex().upper()
    except Exception:
        # Older/newer cryptography API compatibility path.
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.serialization import pkcs12
            password = base64.b64decode(cfg["password_b64"])
            _key, cert, _cas = pkcs12.load_key_and_certificates(key_path.read_bytes(), password)
            return cert.fingerprint(hashes.SHA256()).hex().upper() if cert else None
        except Exception:
            return None


def hashlib_sha256_adapter():
    """Return a cryptography SHA256 algorithm without importing it at module load."""
    from cryptography.hazmat.primitives import hashes
    return hashes.SHA256()


def ensure_signing_identity(log: Callable[[str], None] | None = None) -> tuple[Path, str, str]:
    log = log or (lambda _s: None)
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.x509.oid import NameOID
    except ImportError as e:
        raise PatchError(
            "Automatic signing needs the bundled 'cryptography' dependency. "
            "When running from source: py -m pip install cryptography"
        ) from e

    root = app_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    key_path = root / "signing-key.p12"
    cfg_path = root / "signing.json"
    alias = "spotifybyd"

    loaded = _load_signing_cfg()
    if loaded:
        kp, cfg = loaded
        password = base64.b64decode(cfg["password_b64"]).decode("ascii")
        return kp, cfg.get("alias", alias), password

    log("Creating a private per-user signing key (one time only)...")
    password = secrets.token_urlsafe(24)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "BYD Spotify Patcher Local Key"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Local User"),
        ]
    )
    now = _dt.datetime.now(_dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _dt.timedelta(days=1))
        .not_valid_after(now + _dt.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )
    p12 = pkcs12.serialize_key_and_certificates(
        name=alias.encode("ascii"),
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode("ascii")),
    )
    key_path.write_bytes(p12)
    cfg_path.write_text(
        json.dumps({"password_b64": base64.b64encode(password.encode()).decode(), "alias": alias}, indent=2),
        "utf-8",
    )
    log(f"Signing identity stored in: {root}")
    return key_path, alias, password


def export_signing_identity(destination: str | Path) -> Path:
    ensure_signing_identity()
    root = app_data_dir()
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(root / "signing-key.p12", "signing-key.p12")
        z.write(root / "signing.json", "signing.json")
        z.writestr(
            "README.txt",
            "Sensitive BYD Spotify Patcher signing-key backup. Anyone with this file can sign updates "
            "that Android will accept for APKs signed by this key. Keep it private.\n",
        )
    return dest


def import_signing_identity(source: str | Path) -> str:
    src = Path(source)
    if not src.is_file():
        raise PatchError("Signing-key backup not found")
    try:
        with zipfile.ZipFile(src, "r") as z:
            names = set(z.namelist())
            if not {"signing-key.p12", "signing.json"}.issubset(names):
                raise PatchError("This is not a BYD Spotify Patcher signing-key backup")
            key_bytes = z.read("signing-key.p12")
            cfg_bytes = z.read("signing.json")
    except zipfile.BadZipFile as e:
        raise PatchError("Signing-key backup is not a valid ZIP file") from e

    try:
        cfg = json.loads(cfg_bytes.decode("utf-8"))
        password = base64.b64decode(cfg["password_b64"])
        from cryptography.hazmat.primitives.serialization import pkcs12
        key, cert, _cas = pkcs12.load_key_and_certificates(key_bytes, password)
        if key is None or cert is None:
            raise ValueError("missing key or certificate")
    except Exception as e:
        raise PatchError("Signing-key backup failed cryptographic validation") from e

    root = app_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    # Keep an automatic backup of an existing identity before replacement.
    if (root / "signing-key.p12").exists() and (root / "signing.json").exists():
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        export_signing_identity(root / f"signing-key-before-import-{stamp}.zip")
    (root / "signing-key.p12").write_bytes(key_bytes)
    (root / "signing.json").write_bytes(cfg_bytes)
    fp = cert.fingerprint(hashlib_sha256_adapter()).hex().upper()
    return fp


def import_external_signing_keystore(source: str | Path, password: str, alias: str = "spotifyplus") -> str:
    """Migrate a user's existing PKCS12/JKS signing key into the patcher.

    This is mainly for early testers who already signed Spotify BYD manually and
    want the one-click patcher to keep producing updates Android accepts without
    uninstalling the existing app. New users never need this function.
    """
    src = Path(source)
    if not src.is_file():
        raise PatchError("Existing keystore file not found")
    if not password:
        raise PatchError("Keystore password is required")

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import pkcs12

    key = cert = cas = None
    raw = src.read_bytes()
    # Modern keytool defaults to PKCS12 even if someone happened to name the
    # file .jks, so try direct PKCS12 loading first.
    try:
        key, cert, cas = pkcs12.load_key_and_certificates(raw, password.encode("utf-8"))
    except Exception:
        key = cert = cas = None

    if key is None or cert is None:
        keytool = find_keytool_executable()
        if not keytool:
            raise PatchError(
                "This keystore is not PKCS12 and keytool was not found for JKS conversion. "
                "Run this one-time migration on the PC that has Android Studio/JDK installed."
            )
        with tempfile.TemporaryDirectory(prefix="bydspotify-key-") as td:
            converted = Path(td) / "converted.p12"
            converted_password = secrets.token_urlsafe(24)
            attempts = [None, "JKS"]
            errors: list[str] = []
            for source_type in attempts:
                cmd = [
                    str(keytool), "-importkeystore", "-noprompt",
                    "-srckeystore", str(src),
                    "-srcstorepass", password,
                    "-srcalias", alias,
                    "-destkeystore", str(converted),
                    "-deststoretype", "PKCS12",
                    "-deststorepass", converted_password,
                    "-destkeypass", converted_password,
                    "-destalias", "spotifybyd",
                ]
                if source_type:
                    cmd[2:2] = ["-srcstoretype", source_type]
                cp = subprocess.run(cmd, text=True, capture_output=True)
                if cp.returncode == 0 and converted.is_file():
                    try:
                        key, cert, cas = pkcs12.load_key_and_certificates(
                            converted.read_bytes(), converted_password.encode("utf-8")
                        )
                        if key is not None and cert is not None:
                            break
                    except Exception as e:
                        errors.append(str(e))
                errors.append((cp.stdout + "\n" + cp.stderr).strip())
            if key is None or cert is None:
                raise PatchError("Could not import existing JKS key. Check password/alias.\n" + "\n".join(errors[-2:]))

    root = app_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    if (root / "signing-key.p12").exists() and (root / "signing.json").exists():
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        export_signing_identity(root / f"signing-key-before-external-import-{stamp}.zip")

    local_password = secrets.token_urlsafe(24)
    local_alias = "spotifybyd"
    p12 = pkcs12.serialize_key_and_certificates(
        name=local_alias.encode("ascii"),
        key=key,
        cert=cert,
        cas=cas,
        encryption_algorithm=serialization.BestAvailableEncryption(local_password.encode("ascii")),
    )
    (root / "signing-key.p12").write_bytes(p12)
    (root / "signing.json").write_text(
        json.dumps({"password_b64": base64.b64encode(local_password.encode()).decode(), "alias": local_alias}, indent=2),
        "utf-8",
    )
    return cert.fingerprint(hashlib_sha256_adapter()).hex().upper()


def sign_apk(unsigned_path: str | Path, signed_path: str | Path, log: Callable[[str], None] | None = None) -> Path:
    """Sign and verify the APK without asking the user to manage a keystore.

    A private RSA key/certificate is generated once per user and reused for every
    future update. Portable releases use the AOSP apksigner JAR and a bundled
    minimal Java runtime. Source/development runs fall back to Android Studio's
    SDK if it is installed.
    """
    log = log or (lambda _s: None)
    unsigned = Path(unsigned_path)
    signed = Path(signed_path)
    engine = discover_signing_engine()
    if not engine:
        raise PatchError(
            "No APK signing runtime was found. Build the portable Windows distribution with "
            "build_portable_windows.ps1, or install Android SDK Build Tools for source/development use."
        )

    key_path, alias, password = ensure_signing_identity(log)
    log(f"Signing engine: {engine.description}")

    # Explicitly request the same useful schemes as our proven manual builds.
    # v1 covers older Android versions; v2/v3 cover BYD Android 10 and current
    # phones. v4 is intentionally disabled because it creates a separate .idsig.
    cmd = engine.command_prefix + [
        "sign",
        "--ks", str(key_path),
        "--ks-type", "PKCS12",
        "--ks-key-alias", alias,
        "--ks-pass", f"pass:{password}",
        "--key-pass", f"pass:{password}",
        "--v1-signing-enabled", "true",
        "--v2-signing-enabled", "true",
        "--v3-signing-enabled", "true",
        "--v4-signing-enabled", "false",
        "--out", str(signed),
        str(unsigned),
    ]
    log("Applying Android APK signature…")
    cp = subprocess.run(cmd, text=True, capture_output=True)
    if cp.returncode != 0:
        raise PatchError("apksigner failed:\n" + (cp.stdout + "\n" + cp.stderr).strip())

    verify_cmd = engine.command_prefix + ["verify", "--verbose", "--print-certs", str(signed)]
    cp = subprocess.run(verify_cmd, text=True, capture_output=True)
    verify_text = (cp.stdout + "\n" + cp.stderr).strip()
    if cp.returncode != 0:
        raise PatchError("Final APK signature verification failed:\n" + verify_text)
    # Different apksigner revisions format verbose output slightly differently,
    # so the exit code is authoritative; log the useful scheme/certificate lines.
    useful = [
        line for line in verify_text.splitlines()
        if ("Verified using" in line or "Signer #1 certificate SHA-256" in line or line.startswith("Verifies"))
    ]
    for line in useful:
        log(line)
    log("Signature verification successful.")
    return signed

def patch_and_sign(
    input_path: str | Path,
    output_path: str | Path,
    panel_side: str = PANEL_LEFT,
    log: Callable[[str], None] | None = None,
    instance: str = INSTANCE_PRIMARY,
    app_label: str | None = None,
    icon_hue: int | float | None = None,
) -> PatchReport:
    log = log or print
    output = Path(output_path)
    with tempfile.TemporaryDirectory(prefix="bydspotify-") as td:
        unsigned = Path(td) / "patched-aligned-unsigned.apk"
        report = patch_apk(
            input_path, unsigned, panel_side, log,
            instance=instance, app_label=app_label, icon_hue=icon_hue,
        )
        sign_apk(unsigned, output, log)
        report.output_path = output
        report.output_sha256 = sha256_file(output)
        log(f"Final APK SHA-256: {report.output_sha256}")
        return report


def _default_output(input_path: str, instance: str = INSTANCE_PRIMARY) -> str:
    p = Path(input_path)
    cfg = get_instance_config(instance)
    return str(p.with_name(p.stem + "_BYD" + cfg["output_suffix"] + ".apk"))


def _format_size(n: int) -> str:
    mib = n / (1024 * 1024)
    return f"{mib:.1f} MiB"


def _analysis_text(a: ApkAnalysis) -> str:
    lines = [
        f"Compatibility: {'SUPPORTED' if a.compatible else 'NOT SUPPORTED'}",
        f"Spotify version: {a.spotify_version or 'unknown'} (versionCode {a.spotify_version_code if a.spotify_version_code is not None else 'unknown'})",
        f"Patch profile: {a.profile_name}",
        f"Selected package: {a.target_package}",
        f"Input SHA-256: {a.input_sha256}",
        f"Wide-screen layout SHA-256: {a.wide_layout_sha256 or 'unknown'}",
        f"Size: {_format_size(a.size_bytes)}",
        f"DEX files: {a.dex_count}",
        f"Exact process/package markers: {a.total_dex_package_occurrences}",
        f"Native ABIs: {', '.join(a.native_abis) if a.native_abis else 'none'}",
        f"META-INF/services files: {len(a.services)}",
        f"Known manifest identity strings: {a.manifest_patch_count}",
        f"Known provider matches: {sum(a.resource_matches.values())}",
    ]
    if a.unknown_manifest_strings:
        lines.append("Unknown package-scoped manifest strings (left untouched):")
        lines.extend("  - " + x for x in a.unknown_manifest_strings)
    for d in a.dex:
        if d.exact_package_occurrences:
            lines.append(f"{d.name}: {d.exact_package_occurrences} marker(s), lexical safety={'OK' if d.sort_safe else 'FAIL'}")
            lines.extend("    " + x for x in d.neighbours)
        elif d.error:
            lines.append(f"{d.name}: analysis error: {d.error}")
    if a.warnings:
        lines.append("Warnings:")
        lines.extend("  - " + w for w in a.warnings)
    return "\n".join(lines)



def export_diagnostics(a: ApkAnalysis, destination: str | Path) -> Path:
    """Write a support-safe JSON report containing structure/hashes, never APK payloads."""
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "patcher_version": APP_VERSION,
        "alternate_package": a.target_package,
        "signing_engine": signing_engine_status(),
        "signing_certificate_sha256": signing_certificate_fingerprint(),
        "input_filename": a.input_path.name,
        "input_sha256": a.input_sha256,
        "size_bytes": a.size_bytes,
        "spotify_version": a.spotify_version,
        "spotify_version_code": a.spotify_version_code,
        "profile_name": a.profile_name,
        "wide_layout_sha256": a.wide_layout_sha256,
        "supported_spotify_version": SUPPORTED_SPOTIFY_VERSION,
        "compatible": a.compatible,
        "dex_count": a.dex_count,
        "total_dex_package_occurrences": a.total_dex_package_occurrences,
        "native_abis": a.native_abis,
        "services": a.services,
        "manifest_patch_count": a.manifest_patch_count,
        "unknown_manifest_strings": a.unknown_manifest_strings,
        "resource_matches": a.resource_matches,
        "warnings": a.warnings,
        "dex": [asdict(d) for d in a.dex],
    }
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), "utf-8")
    return dest

def run_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
    from PIL import ImageTk

    root = tk.Tk()
    root.withdraw()  # avoid a visible top-left flash before final sizing/centering
    root.title(f"BYD Spotify Patcher v{APP_VERSION}")

    def desktop_work_area() -> tuple[int, int, int, int]:
        """Return usable desktop x/y/width/height in Tk coordinate units."""
        screen_w = max(1, int(root.winfo_screenwidth()))
        screen_h = max(1, int(root.winfo_screenheight()))
        left, top, right, bottom = 0, 0, screen_w, screen_h

        # On Windows, exclude the taskbar. Scale the Win32 coordinates back to
        # Tk units when display scaling/DPI virtualisation makes them differ.
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                rect = wintypes.RECT()
                SPI_GETWORKAREA = 0x0030
                ok = ctypes.windll.user32.SystemParametersInfoW(
                    SPI_GETWORKAREA, 0, ctypes.byref(rect), 0
                )
                if ok:
                    native_w = max(1, int(ctypes.windll.user32.GetSystemMetrics(0)))
                    native_h = max(1, int(ctypes.windll.user32.GetSystemMetrics(1)))
                    sx = screen_w / native_w
                    sy = screen_h / native_h
                    left = int(round(rect.left * sx))
                    top = int(round(rect.top * sy))
                    right = int(round(rect.right * sx))
                    bottom = int(round(rect.bottom * sy))
            except Exception:
                pass

        return left, top, max(1, right - left), max(1, bottom - top)

    # Keep the log compact on shorter/scaled desktops so the action/signing
    # controls at the bottom are visible immediately without manual resizing.
    _work_x, _work_y, _work_w, _work_h = desktop_work_area()
    if _work_h <= 760:
        log_lines = 4
    elif _work_h <= 820:
        log_lines = 7
    elif _work_h <= 950:
        log_lines = 10
    elif _work_h <= 1100:
        log_lines = 13
    else:
        log_lines = 16

    input_var = tk.StringVar()
    output_var = tk.StringVar()
    status_var = tk.StringVar(value="Select an original Spotify APK (com.spotify.music).")
    compat_var = tk.StringVar(value="Not analysed")
    key_var = tk.StringVar(value="Signing key: will be created automatically")
    signer_var = tk.StringVar(value="Signing engine: " + signing_engine_status())
    panel_var = tk.StringVar(value=PANEL_RIGHT)
    panel_desc_var = tk.StringVar(value="Right / RHD: v9 text + compact lists, with the v14 navigation/player panel moved to the right.")
    instance_var = tk.StringVar(value=INSTANCE_PRIMARY)
    app_label_var = tk.StringVar(value=INSTANCE_CONFIG[INSTANCE_PRIMARY]["label"])
    hue_var = tk.IntVar(value=INSTANCE_CONFIG[INSTANCE_PRIMARY]["hue"])
    package_var = tk.StringVar(value=INSTANCE_CONFIG[INSTANCE_PRIMARY]["package"])
    instance_desc_var = tk.StringVar(value="com.spotify.musib — main SpotifyPlus profile.")
    preview_note_var = tk.StringVar(value="Select an APK")
    preview_cache = {"apk_path": None, "icon": None, "photo": None}
    last_analysis: dict[str, ApkAnalysis | None] = {"value": None}

    frm = ttk.Frame(root, padding=14)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="BYD Spotify Patcher", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(
        frm,
        text=f"Spotify {SUPPORTED_SPOTIFY_VERSION} BYD profile. Spotify is supplied by the user and patched locally.",
    ).pack(anchor="w", pady=(0, 12))

    row1 = ttk.Frame(frm)
    row1.pack(fill="x", pady=4)
    ttk.Label(row1, text="Original Spotify APK", width=20).pack(side="left")
    ttk.Entry(row1, textvariable=input_var).pack(side="left", fill="x", expand=True, padx=6)

    def clear_analysis():
        last_analysis["value"] = None
        compat_var.set("Not analysed")

    def browse_input():
        p = filedialog.askopenfilename(filetypes=[("Android APK", "*.apk"), ("All files", "*.*")])
        if p:
            input_var.set(p)
            output_var.set(_default_output(p, instance_var.get()))
            clear_analysis()

    ttk.Button(row1, text="Browse…", command=browse_input).pack(side="left")

    row2 = ttk.Frame(frm)
    row2.pack(fill="x", pady=4)
    ttk.Label(row2, text="Output APK", width=20).pack(side="left")
    ttk.Entry(row2, textvariable=output_var).pack(side="left", fill="x", expand=True, padx=6)

    def browse_output():
        p = filedialog.asksaveasfilename(defaultextension=".apk", filetypes=[("Android APK", "*.apk")])
        if p:
            output_var.set(p)

    ttk.Button(row2, text="Save as…", command=browse_output).pack(side="left")

    profile_row = ttk.Frame(frm)
    profile_row.pack(fill="x", pady=(8, 2))

    profile_controls = ttk.Frame(profile_row)
    profile_controls.pack(side="left", fill="x", expand=True)

    instance_row = ttk.Frame(profile_controls)
    instance_row.pack(fill="x", pady=(0, 2))
    ttk.Label(instance_row, text="App instance (for separate Spotify profiles)").pack(side="left")

    def update_instance():
        cfg = get_instance_config(instance_var.get())
        package_var.set(cfg["package"])
        app_label_var.set(cfg["label"])
        hue_var.set(cfg["hue"])
        if instance_var.get() == INSTANCE_SECONDARY:
            instance_desc_var.set(f"{cfg['package']} — second separate Spotify profile.")
        else:
            instance_desc_var.set(f"{cfg['package']} — main SpotifyPlus profile.")
        src = input_var.get().strip()
        if src:
            output_var.set(_default_output(src, instance_var.get()))
        clear_analysis()

    ttk.Radiobutton(
        instance_row, text="Primary", variable=instance_var, value=INSTANCE_PRIMARY, command=update_instance
    ).pack(side="left", padx=(12, 12))
    ttk.Radiobutton(
        instance_row, text="Secondary", variable=instance_var, value=INSTANCE_SECONDARY, command=update_instance
    ).pack(side="left", padx=(0, 12))
    ttk.Label(profile_controls, textvariable=instance_desc_var).pack(anchor="w", padx=(166, 0), pady=(0, 2))

    package_row = ttk.Frame(profile_controls)
    package_row.pack(fill="x", pady=2)
    ttk.Label(package_row, text="Internal package", width=20).pack(side="left")
    ttk.Label(package_row, textvariable=package_var).pack(side="left", padx=6)

    label_row = ttk.Frame(profile_controls)
    label_row.pack(fill="x", pady=2)
    ttk.Label(label_row, text="Visible app name", width=20).pack(side="left")
    ttk.Entry(label_row, textvariable=app_label_var, width=30).pack(side="left", padx=6)
    ttk.Label(label_row, text=f"max {MAX_APP_LABEL_LEN} characters").pack(side="left")

    hue_row = ttk.Frame(profile_controls)
    hue_row.pack(fill="x", pady=(2, 6))
    ttk.Label(hue_row, text="Logo hue shift", width=20).pack(side="left")
    tk.Scale(
        hue_row, from_=0, to=359, orient="horizontal", variable=hue_var, resolution=1,
        showvalue=True, length=360, highlightthickness=0
    ).pack(side="left", padx=2)
    ttk.Label(hue_row, text="degrees (0 = original green)").pack(side="left", padx=(6, 0))

    preview_box = ttk.LabelFrame(profile_row, text="Logo preview", padding=6)
    preview_box.pack(side="right", padx=(12, 4), anchor="n")
    preview_label = ttk.Label(preview_box, anchor="center")
    preview_label.pack()
    ttk.Label(preview_box, textvariable=preview_note_var, anchor="center").pack(fill="x", pady=(3, 0))

    def refresh_logo_preview(*_):
        apk_path = input_var.get().strip()
        if apk_path != preview_cache["apk_path"]:
            preview_cache["apk_path"] = apk_path
            preview_cache["icon"] = load_preview_icon_from_apk(apk_path)

        try:
            hue = normalise_hue(hue_var.get())
        except (PatchError, tk.TclError):
            return

        img = build_logo_preview_image(preview_cache["icon"], hue, size=112)
        photo = ImageTk.PhotoImage(img)
        preview_cache["photo"] = photo
        preview_label.configure(image=photo)
        preview_note_var.set(f"Hue {hue}°" if preview_cache["icon"] is not None else "Select an APK")

    input_var.trace_add("write", refresh_logo_preview)
    hue_var.trace_add("write", refresh_logo_preview)
    refresh_logo_preview()

    side_row = ttk.Frame(frm)
    side_row.pack(fill="x", pady=(8, 2))
    ttk.Label(side_row, text="Side panel position", width=20).pack(side="left")

    def update_panel_description():
        if panel_var.get() == PANEL_LEFT:
            panel_desc_var.set("Left / LHD: proven v9 compact/larger-text layout; navigation and mini-player stay on the left.")
        else:
            panel_desc_var.set("Right / RHD: same v9 text/spacing plus the proven v14 navigation/player panel on the right.")

    ttk.Radiobutton(
        side_row, text="Left (LHD)", variable=panel_var, value=PANEL_LEFT, command=update_panel_description
    ).pack(side="left", padx=(6, 16))
    ttk.Radiobutton(
        side_row, text="Right (RHD)", variable=panel_var, value=PANEL_RIGHT, command=update_panel_description
    ).pack(side="left")
    ttk.Label(frm, textvariable=panel_desc_var).pack(anchor="w", padx=(166, 0), pady=(0, 4))

    info_row = ttk.Frame(frm)
    info_row.pack(fill="x", pady=(8, 5))
    ttk.Label(info_row, text="Pre-flight:", font=("Segoe UI", 9, "bold")).pack(side="left")
    ttk.Label(info_row, textvariable=compat_var).pack(side="left", padx=(6, 16))
    ttk.Label(info_row, textvariable=key_var).pack(side="left")
    ttk.Label(info_row, textvariable=signer_var).pack(side="right")

    ttk.Separator(frm).pack(fill="x", pady=8)
    logbox = tk.Text(frm, height=log_lines, wrap="word", state="disabled", font=("Consolas", 9))
    logbox.pack(fill="both", expand=True)

    def ui_log(s: str):
        def append():
            logbox.configure(state="normal")
            logbox.insert("end", s + "\n")
            logbox.see("end")
            logbox.configure(state="disabled")
        root.after(0, append)

    def refresh_key_label():
        fp = signing_certificate_fingerprint()
        if fp:
            key_var.set("Signing key: " + ":".join(fp[i:i+2] for i in range(0, min(len(fp), 24), 2)) + "…")
        else:
            key_var.set("Signing key: will be created automatically")

    refresh_key_label()

    progress = ttk.Progressbar(frm, mode="indeterminate")
    progress.pack(fill="x", pady=(10, 4))
    ttk.Label(frm, textvariable=status_var).pack(anchor="w")

    btnrow = ttk.Frame(frm)
    btnrow.pack(fill="x", pady=(10, 0))

    analyse_btn = ttk.Button(btnrow, text="ANALYSE APK")
    analyse_btn.pack(side="left")
    patch_btn = ttk.Button(btnrow, text="PATCH + SIGN", state="disabled")
    patch_btn.pack(side="left", padx=(8, 0))

    def set_busy(busy: bool):
        if busy:
            analyse_btn.configure(state="disabled")
            patch_btn.configure(state="disabled")
            progress.start(12)
        else:
            analyse_btn.configure(state="normal")
            a = last_analysis["value"]
            patch_btn.configure(state="normal" if a and a.compatible else "disabled")
            progress.stop()

    def do_analyse():
        src = input_var.get().strip()
        if not src:
            messagebox.showerror("Missing file", "Select an original Spotify APK first.")
            return
        cfg = get_instance_config(instance_var.get())
        target_package = cfg["package"]
        set_busy(True)
        status_var.set("Analysing APK structure…")
        ui_log("=" * 72)
        ui_log(f"Analysing: {src}")
        ui_log(f"Target package: {target_package}")

        def worker():
            try:
                a = analyse_apk(src, ui_log, target_package)
                last_analysis["value"] = a
                ui_log(_analysis_text(a))
                compat_text = "SUPPORTED" if a.compatible else "NOT SUPPORTED"
                root.after(0, lambda: compat_var.set(compat_text))
                root.after(0, lambda: status_var.set(
                    "Ready to patch." if a.compatible else "Unsupported structure — no APK will be created."
                ))
            except Exception as e:
                last_analysis["value"] = None
                ui_log("ERROR: " + str(e))
                root.after(0, lambda: compat_var.set("Analysis failed"))
                root.after(0, lambda: status_var.set("Analysis failed — see log."))
                root.after(0, lambda: messagebox.showerror("Analysis failed", str(e)))
            finally:
                root.after(0, lambda: set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    analyse_btn.configure(command=do_analyse)

    def do_patch():
        src = input_var.get().strip()
        dst = output_var.get().strip()
        a = last_analysis["value"]
        if not src or not dst:
            messagebox.showerror("Missing file", "Select an input APK and output location.")
            return
        if not a or not a.compatible:
            messagebox.showerror("Analyse first", "Run ANALYSE APK and resolve any compatibility failure first.")
            return
        try:
            selected_label = validate_app_label(app_label_var.get())
            selected_hue = normalise_hue(hue_var.get())
        except Exception as e:
            messagebox.showerror("Branding option", str(e))
            return
        selected_instance = instance_var.get()
        set_busy(True)
        status_var.set("Patching, aligning, signing and verifying…")
        ui_log("=" * 72)
        ui_log(f"Input:  {src}")
        ui_log(f"Output: {dst}")
        ui_log(f"Instance: {get_instance_config(selected_instance)['title']} ({package_var.get()})")
        ui_log(f"Visible name: {selected_label}")
        ui_log(f"Icon hue: {selected_hue}°")
        ui_log("Panel:  " + ("Left / LHD" if panel_var.get() == PANEL_LEFT else "Right / RHD"))

        def worker():
            try:
                report = patch_and_sign(
                    src, dst, panel_var.get(), ui_log,
                    instance=selected_instance, app_label=selected_label, icon_hue=selected_hue,
                )
                for w in report.warnings:
                    ui_log("WARNING: " + w)
                ui_log(f"Manifest strings patched: {len(report.manifest_changes)}")
                ui_log(f"DEX entries patched: {report.dex_changes}")
                ui_log(f"UI resource values patched: {report.ui_changes}")
                ui_log(f"Panel side: {report.panel_side}")
                ui_log(f"Package: {report.package_name}")
                ui_log(f"Visible name: {report.app_label}")
                ui_log(f"Icon hue: {report.icon_hue}°")
                ui_log(f"Runtime service files preserved: {report.services_preserved}")
                ui_log(f"Final SHA-256: {report.output_sha256}")
                root.after(0, refresh_key_label)
                root.after(0, lambda: status_var.set("Ready — patched APK is signed and verified."))
                root.after(0, lambda: messagebox.showinfo("Done", f"Ready to install:\n{dst}"))
            except Exception as e:
                ui_log("ERROR: " + str(e))
                root.after(0, lambda: status_var.set("Failed — see log."))
                root.after(0, lambda: messagebox.showerror("Patch failed", str(e)))
            finally:
                root.after(0, lambda: set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    patch_btn.configure(command=do_patch)

    def open_folder():
        p = Path(output_var.get().strip()).parent
        if os.name == "nt" and p.exists():
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif p.exists():
            subprocess.Popen(["xdg-open", str(p)])

    ttk.Button(btnrow, text="Open output folder", command=open_folder).pack(side="left", padx=8)

    def export_diag():
        a = last_analysis["value"]
        if not a:
            messagebox.showerror("Analyse first", "Run ANALYSE APK before exporting diagnostics.")
            return
        default = Path(a.input_path).stem + "_BYD_diagnostics.json"
        dest = filedialog.asksaveasfilename(
            defaultextension=".json", initialfile=default, filetypes=[("JSON diagnostics", "*.json")]
        )
        if not dest:
            return
        try:
            export_diagnostics(a, dest)
            messagebox.showinfo("Diagnostics saved", "Support-safe diagnostics saved. The file contains hashes and APK structure, not Spotify code.")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    ttk.Button(btnrow, text="Export diagnostics…", command=export_diag).pack(side="left", padx=4)

    keyrow = ttk.Frame(frm)
    keyrow.pack(fill="x", pady=(8, 0))
    ttk.Label(keyrow, text="Update signing key:", font=("Segoe UI", 9, "bold")).pack(side="left")

    def prepare_key():
        try:
            ensure_signing_identity(ui_log)
            refresh_key_label()
            messagebox.showinfo("Signing key ready", "A private signing identity is ready. The same key will be reused automatically for future Spotify BYD updates.")
        except Exception as e:
            messagebox.showerror("Key creation failed", str(e))

    ttk.Button(keyrow, text="Create / show key", command=prepare_key).pack(side="left", padx=(8, 4))

    def import_existing_keystore_gui():
        src = filedialog.askopenfilename(
            title="Import existing Android signing keystore",
            filetypes=[("Android keystore", "*.jks *.p12 *.pfx"), ("All files", "*.*")],
        )
        if not src:
            return
        password = simpledialog.askstring("Keystore password", "Password for the existing keystore:", show="*")
        if password is None:
            return
        alias = simpledialog.askstring("Key alias", "Key alias (your earlier manual key used spotifyplus):", initialvalue="spotifyplus")
        if not alias:
            return
        try:
            fp = import_external_signing_keystore(src, password, alias)
            refresh_key_label()
            messagebox.showinfo(
                "Existing key imported",
                "The patcher will now sign with your existing Android key, so future APKs can update an installation signed by that key.\n\nCertificate SHA-256:\n" + fp,
            )
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    ttk.Button(keyrow, text="Import existing JKS/P12…", command=import_existing_keystore_gui).pack(side="left", padx=4)

    def export_key():
        try:
            default = "BYDSpotifyPatcher-signing-key-backup.zip"
            dest = filedialog.asksaveasfilename(
                defaultextension=".zip", initialfile=default, filetypes=[("ZIP backup", "*.zip")]
            )
            if not dest:
                return
            export_signing_identity(dest)
            refresh_key_label()
            messagebox.showinfo(
                "Key exported",
                "Signing-key backup saved. Keep it private; it is needed to keep updating the same Spotify BYD installation from another PC.",
            )
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def import_key():
        src = filedialog.askopenfilename(filetypes=[("ZIP backup", "*.zip"), ("All files", "*.*")])
        if not src:
            return
        if not messagebox.askyesno(
            "Replace signing key?",
            "Importing a different key changes which existing Spotify BYD installation this PC can update. "
            "The current key will be backed up automatically. Continue?",
        ):
            return
        try:
            fp = import_signing_identity(src)
            refresh_key_label()
            messagebox.showinfo("Key imported", "Signing key restored. Certificate SHA-256:\n" + fp)
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    ttk.Button(keyrow, text="Export backup…", command=export_key).pack(side="left", padx=4)
    ttk.Button(keyrow, text="Import backup…", command=import_key).pack(side="left", padx=4)
    ttk.Button(keyrow, text="Exit", command=root.destroy).pack(side="right")

    def size_and_center_window():
        """Fit the GUI inside the usable desktop and center it before showing."""
        root.update_idletasks()

        work_x, work_y, work_w, work_h = desktop_work_area()
        requested_w = max(1, int(root.winfo_reqwidth()))
        requested_h = max(1, int(root.winfo_reqheight()))

        # Keep a small drag/resize margin inside the usable work area.
        margin = 16
        max_w = max(760, work_w - margin * 2)
        max_h = max(600, work_h - margin * 2)

        target_w = min(max(requested_w, 920), max_w)
        target_h = min(max(requested_h, 700), max_h)

        x = work_x + max(0, (work_w - target_w) // 2)
        y = work_y + max(0, (work_h - target_h) // 2)

        root.geometry(f"{target_w}x{target_h}+{x}+{y}")
        root.minsize(min(820, target_w), min(600, target_h))

    size_and_center_window()
    root.deiconify()
    root.mainloop()


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Patch Spotify APK for BYD coexistence")
    parser.add_argument("input", nargs="?", help="original Spotify APK")
    parser.add_argument("output", nargs="?", help="output APK")
    parser.add_argument("--unsigned", action="store_true", help="patch/alignment only; do not sign")
    parser.add_argument(
        "--panel-side", choices=[PANEL_LEFT, PANEL_RIGHT], default=PANEL_LEFT,
        help="wide-screen navigation/player side: left=v9/LHD, right=v14/RHD (default: left)",
    )
    parser.add_argument(
        "--instance", choices=[INSTANCE_PRIMARY, INSTANCE_SECONDARY], default=INSTANCE_PRIMARY,
        help="clone identity: primary=musib, secondary=musia",
    )
    parser.add_argument("--app-label", help=f"visible launcher name (max {MAX_APP_LABEL_LEN} characters)")
    parser.add_argument("--icon-hue", type=int, help="launcher icon hue rotation in degrees (0-359)")
    parser.add_argument("--analyse", action="store_true", help="analyse compatibility only")
    parser.add_argument("--diagnostics", metavar="JSON", help="analyse and export support-safe diagnostics JSON")
    parser.add_argument("--gui", action="store_true", help="open GUI")
    parser.add_argument("--export-key", metavar="ZIP", help="export signing-key backup")
    parser.add_argument("--import-key", metavar="ZIP", help="import signing-key backup")
    parser.add_argument("--import-keystore", metavar="FILE", help="migrate an existing JKS/PKCS12 Android signing key")
    parser.add_argument("--keystore-password", help="password for --import-keystore")
    parser.add_argument("--keystore-alias", default="spotifyplus", help="key alias for --import-keystore (default: spotifyplus)")
    args = parser.parse_args(argv)

    try:
        if args.export_key:
            print(export_signing_identity(args.export_key))
            return 0
        if args.import_key:
            print("Imported certificate SHA-256:", import_signing_identity(args.import_key))
            return 0
        if args.import_keystore:
            if not args.keystore_password:
                raise PatchError("--keystore-password is required with --import-keystore")
            print("Imported existing certificate SHA-256:", import_external_signing_keystore(
                args.import_keystore, args.keystore_password, args.keystore_alias
            ))
            return 0
        if args.gui or not args.input:
            run_gui()
            return 0
        cfg = get_instance_config(args.instance)
        target_package = cfg["package"]
        app_label = validate_app_label(args.app_label if args.app_label is not None else cfg["label"])
        icon_hue = normalise_hue(args.icon_hue if args.icon_hue is not None else cfg["hue"])
        if args.diagnostics:
            a = analyse_apk(args.input, target_package=target_package)
            export_diagnostics(a, args.diagnostics)
            print(_analysis_text(a))
            print("Diagnostics:", args.diagnostics)
            return 0
        if args.analyse:
            print(_analysis_text(analyse_apk(
                args.input, target_package=target_package
            )))
            return 0
        output = args.output or _default_output(args.input, args.instance)
        if args.unsigned:
            r = patch_apk(
                args.input, output, args.panel_side, print,
                instance=args.instance, app_label=app_label, icon_hue=icon_hue,
            )
        else:
            r = patch_and_sign(
                args.input, output, args.panel_side, print,
                instance=args.instance, app_label=app_label, icon_hue=icon_hue,
            )
        for w in r.warnings:
            print("WARNING:", w)
        print("Ready:", r.output_path)
        return 0
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
