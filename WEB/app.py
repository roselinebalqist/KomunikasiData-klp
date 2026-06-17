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
