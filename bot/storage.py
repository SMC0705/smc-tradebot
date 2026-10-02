"""Speichern und Laden: Zustand der Bots (state/), Einstellungen der App (config/) und
die Übersicht für die App (docs/data/status.json). Alle Pfade stehen in settings.py."""
import json
import os

from . import settings as S


def _path(name):
    return os.path.join(S.STATE_DIR, f"{name}.json")


def read(name, default=None):
    """Zustand lesen, z. B. read("pool") oder read("scalp")."""
    try:
        with open(_path(name)) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write(name, data):
    os.makedirs(S.STATE_DIR, exist_ok=True)
    with open(_path(name), "w") as f:
        json.dump(data, f, separators=(",", ":"))


def read_config(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def write_status(status):
    os.makedirs(os.path.dirname(S.STATUS_FILE), exist_ok=True)
    with open(S.STATUS_FILE, "w") as f:
        json.dump(status, f, separators=(",", ":"))
