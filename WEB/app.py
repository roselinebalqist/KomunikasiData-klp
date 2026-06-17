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


def normalize_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    received_at = datetime.now()
    description = safe_text(payload.get("description"), "Laporan tanpa detail")
    urgency = safe_text(payload.get("urgency"), "Sedang")
    if urgency not in URGENCY_SCORE:
        urgency = "Sedang"

    normalized = {
        "ticket_id": generate_ticket_id(payload, received_at),
        "received_at": received_at.strftime("%Y-%m-%d %H:%M:%S"),
        "source": safe_text(payload.get("source"), "Web"),
        "sender": "Anonim",
        "category": safe_text(payload.get("category"), "Lainnya"),
        "location": safe_text(payload.get("location"), "Tidak disebutkan"),
        "urgency": urgency,
        "priority": determine_priority(urgency, description),
        "status": "Masuk antrean verifikasi",
        "description": description,
        "impact": safe_text(payload.get("impact"), "Belum dijelaskan"),
        "contact_code": safe_text(payload.get("contact_code"), "Anonim penuh"),
    }
    return normalized


def build_stats():
    total = len(reports)
    urgency_counter = Counter(report.get("urgency", "Sedang") for report in reports)
    category_counter = Counter(report.get("category", "Lainnya") for report in reports)
    p1_total = sum(1 for report in reports if report.get("priority", "").startswith("P1"))
    latest_time = reports[-1]["received_at"] if reports else "Belum ada laporan"

    return {
        "total": total,
        "critical": urgency_counter.get("Kritis", 0),
        "high": urgency_counter.get("Tinggi", 0),
        "p1": p1_total,
        "latest_time": latest_time,
        "top_category": category_counter.most_common(1)[0][0] if category_counter else "-",
    }


reports.extend(load_reports())


@app.route("/")
def app_page():
    return render_template("app.html", stats=build_stats())


@app.route("/admin")
def admin_page():
    # Backward compatibility: admin tetap bisa dibuka, tapi diarahkan ke alamat utama.
    return redirect("/#admin")


@app.route("/api/admin/session")
def api_admin_session():
    return jsonify({"authenticated": bool(session.get("is_admin"))})


@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.get_json(silent=True) or {}
    pin = str(data.get("pin", "")).strip()

    if pin == ADMIN_PIN:
        session["is_admin"] = True
        return jsonify({"status": "success", "message": "Akses admin berhasil dibuka."})

    return jsonify({"status": "error", "message": "PIN admin salah."}), 401


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.pop("is_admin", None)
    return jsonify({"status": "success", "message": "Akses admin dikunci kembali."})
