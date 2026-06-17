import json
import socket
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent
KEY_PATH = BASE_DIR / "secret.key"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000

CATEGORY_OPTIONS = {
    "1": "Gedung & Ruangan",
    "2": "Listrik & Internet",
    "3": "Air & Sanitasi",
    "4": "Keamanan",
    "5": "Kebersihan",
    "6": "Lainnya",
}

URGENCY_OPTIONS = {
    "1": "Rendah",
    "2": "Sedang",
    "3": "Tinggi",
    "4": "Kritis",
}


def load_cipher():
    if not KEY_PATH.exists():
        raise FileNotFoundError(
            "secret.key belum ada. Jalankan 'python generate_key.py' dulu, lalu pakai key yang sama dengan server."
        )
    return Fernet(KEY_PATH.read_bytes())


def choose_option(title, options):
    print(f"\n{title}")
    for key, value in options.items():
        print(f"  {key}. {value}")

    while True:
        choice = input("Pilih nomor: ").strip()
        if choice in options:
            return options[choice]
        print("Pilihan nggak valid. Jangan bikin server ikut pusing, Pi.")


def build_report_payload():
    category = choose_option("Kategori laporan", CATEGORY_OPTIONS)
    location = input("Lokasi spesifik        : ").strip()
    urgency = choose_option("Tingkat urgensi", URGENCY_OPTIONS)
    description = input("Detail masalah         : ").strip()
    impact = input("Dampak ke mahasiswa    : ").strip()
    contact_code = input("Kode pelapor opsional  : ").strip() or "Anonim penuh"

    if not location or not description:
        print("Lokasi dan detail masalah wajib diisi. Server bukan cenayang, Pi.")
        return None

    return {
        "source": "CLI",
        "category": category,
        "location": location,
        "urgency": urgency,
        "description": description,
        "impact": impact or "Belum dijelaskan",
        "contact_code": contact_code,
        "created_at_client": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def start_client():
    cipher = load_cipher()

    print("\n=== Secure Campus Report CLI ===")
    print("Mode: anonim, terenkripsi, dan multi-client via TCP")
    print("Ketik 'exit' di alamat server untuk keluar.\n")

    host = input(f"Alamat server [{DEFAULT_HOST}]: ").strip() or DEFAULT_HOST
    if host.lower() == "exit":
        return

    raw_port = input(f"Port server [{DEFAULT_PORT}]: ").strip()
    port = int(raw_port or DEFAULT_PORT)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    print("\nTerhubung ke server. Isi laporan insiden fasilitas kampus di bawah ini.")
    print("Ketik CTRL+C untuk berhenti.\n")

    try:
        while True:
            payload = build_report_payload()
            if not payload:
                continue

            encrypted_message = cipher.encrypt(json.dumps(payload).encode("utf-8"))
            client_socket.sendall(encrypted_message)

            encrypted_response = client_socket.recv(4096)
            response = json.loads(cipher.decrypt(encrypted_response).decode("utf-8"))

            print("\n--- Bukti Penerimaan Server ---")
            print(f"Status    : {response.get('status')}")
            print(f"Ticket ID : {response.get('ticket_id')}")
            print(f"Prioritas : {response.get('priority')}")
            print(f"Pesan     : {response.get('message')}")
            print("--------------------------------\n")

            again = input("Kirim laporan lain? [y/N]: ").strip().lower()
            if again != "y":
                break

    except KeyboardInterrupt:
        print("\nClient dihentikan.")
    finally:
        client_socket.close()
        print("Koneksi ditutup.")


if __name__ == "__main__":
    start_client()
