import hashlib
import json
import socket
import threading
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

BASE_DIR = Path(__file__).resolve().parent
KEY_PATH = BASE_DIR / "secret.key"
LOG_PATH = BASE_DIR / "reports_cli.jsonl"
HOST = "0.0.0.0"
PORT = 5000

clients = []
clients_lock = threading.Lock()
log_lock = threading.Lock()

URGENCY_SCORE = {
    "Rendah": 1,
    "Sedang": 2,
    "Tinggi": 3,
    "Kritis": 4,
}


def load_cipher():
    if not KEY_PATH.exists():
        KEY_PATH.write_bytes(Fernet.generate_key())
        print(f"[KEY] secret.key belum ada, dibuat otomatis di {KEY_PATH}")
        print("[KEY] Kalau client beda laptop, copy file secret.key ini ke folder CLI client.")
    return Fernet(KEY_PATH.read_bytes())


cipher = load_cipher()


def normalize_report(payload, addr):
    now = datetime.now()
    urgency = payload.get("urgency", "Sedang")
    score = URGENCY_SCORE.get(urgency, 2)
    priority = "P1 - Tanggap cepat" if score >= 4 else "P2 - Prioritas tinggi" if score == 3 else "P3 - Normal"

    seed = "|".join([
        now.isoformat(),
        str(addr),
        payload.get("category", ""),
        payload.get("location", ""),
        payload.get("description", ""),
    ])
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest().upper()

    return {
        "ticket_id": f"INC-{now.strftime('%y%m%d')}-{digest[:6]}",
        "received_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source": payload.get("source", "CLI"),
        "sender": "Anonim",
        "category": payload.get("category", "Lainnya"),
        "location": payload.get("location", "Tidak disebutkan"),
        "urgency": urgency,
        "priority": priority,
        "status": "Masuk antrean verifikasi",
        "description": payload.get("description", ""),
        "impact": payload.get("impact", "Belum dijelaskan"),
        "contact_code": payload.get("contact_code", "Anonim penuh"),
        "client_address": f"{addr[0]}:{addr[1]}",
    }


def save_report(report):
    with log_lock:
        with LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(json.dumps(report, ensure_ascii=False) + "\n")


def print_report(report):
    print("\n========== LAPORAN MASUK ==========")
    print(f"Ticket ID : {report['ticket_id']}")
    print(f"Waktu     : {report['received_at']}")
    print(f"Sumber    : {report['source']} dari {report['client_address']}")
    print(f"Kategori  : {report['category']}")
    print(f"Lokasi    : {report['location']}")
    print(f"Urgensi   : {report['urgency']} ({report['priority']})")
    print(f"Status    : {report['status']}")
    print(f"Detail    : {report['description']}")
    print(f"Dampak    : {report['impact']}")
    print("===================================\n")


def handle_client(conn, addr):
    print(f"[TERHUBUNG] Client dari {addr}")
    with clients_lock:
        clients.append(conn)

    try:
        while True:
            encrypted_data = conn.recv(8192)
            if not encrypted_data:
                break

            try:
                decrypted_text = cipher.decrypt(encrypted_data).decode("utf-8")
                payload = json.loads(decrypted_text)
                report = normalize_report(payload, addr)
                save_report(report)
                print_report(report)

                response = {
                    "status": "success",
                    "ticket_id": report["ticket_id"],
                    "priority": report["priority"],
                    "message": "Laporan terenkripsi berhasil diterima server dan dicatat ke log.",
                }
                conn.sendall(cipher.encrypt(json.dumps(response).encode("utf-8")))

            except InvalidToken:
                response = {
                    "status": "error",
                    "ticket_id": "-",
                    "priority": "-",
                    "message": "Token enkripsi tidak valid. Pastikan secret.key server dan client sama.",
                }
                conn.sendall(cipher.encrypt(json.dumps(response).encode("utf-8")))
            except json.JSONDecodeError:
                response = {
                    "status": "error",
                    "ticket_id": "-",
                    "priority": "-",
                    "message": "Format data tidak valid. Client harus mengirim JSON terenkripsi.",
                }
                conn.sendall(cipher.encrypt(json.dumps(response).encode("utf-8")))

    except ConnectionResetError:
        print(f"[PUTUS] Client {addr} terputus tiba-tiba.")
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()
        print(f"[KONEKSI DITUTUP] {addr}")


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print("=== Secure Campus Report Server CLI ===")
    print(f"[SERVER AKTIF] Listening di {HOST}:{PORT}")
    print(f"[LOG] Laporan disimpan ke {LOG_PATH}")
    print("[MODE] TCP multithreading + Fernet symmetric encryption\n")

    while True:
        conn, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        client_thread.start()


if __name__ == "__main__":
    start_server()
