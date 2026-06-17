import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import os

from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_socketio import SocketIO

BASE_DIR = Path(__file__).resolve().parent
KEY_PATH = BASE_DIR / "secret.key"
LOG_PATH = BASE_DIR / "reports_web.jsonl"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("APP_SECRET_KEY", "secure-campus-report-demo")
ADMIN_PIN = os.getenv("ADMIN_PIN", "admin123")

# async_mode="threading" membuat project lebih gampang dijalankan tanpa eventlet/gevent.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

if not KEY_PATH.exists():
    KEY_PATH.write_bytes(Fernet.generate_key())

cipher = Fernet(KEY_PATH.read_bytes())

URGENCY_SCORE = {
    "Rendah": 1,
    "Sedang": 2,
    "Tinggi": 3,
    "Kritis": 4,
}

KEYWORD_BOOST = [
    "kebakaran",
    "asap",
    "korslet",
    "banjir",
    "ambruk",
    "pecah",
    "hilang",
    "maling",
    "cedera",
    "darurat",
]

reports = []

def safe_text(value: Any, default: str = "") -> str:
    text = str(value or default).strip()
    return text[:1000]


def load_reports():
    if not LOG_PATH.exists():
        return []

    loaded = []
    with LOG_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                loaded.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return loaded


def save_report(report: Dict[str, Any]):
    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(report, ensure_ascii=False) + "\n")


def determine_priority(urgency: str, description: str) -> str:
    score = URGENCY_SCORE.get(urgency, 2)
    lower_description = description.lower()

    if any(keyword in lower_description for keyword in KEYWORD_BOOST):
        score = min(score + 1, 4)

    if score >= 4:
        return "P1 - Tanggap cepat"
    if score == 3:
        return "P2 - Prioritas tinggi"
    return "P3 - Normal"


def generate_ticket_id(payload: Dict[str, Any], received_at: datetime) -> str:
    seed = "|".join([
        received_at.isoformat(),
        payload.get("category", ""),
        payload.get("location", ""),
        payload.get("description", ""),
    ])
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest().upper()
    return f"INC-{received_at.strftime('%y%m%d')}-{digest[:6]}"
