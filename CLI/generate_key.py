from pathlib import Path
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent
KEY_PATH = BASE_DIR / "secret.key"

key = Fernet.generate_key()
KEY_PATH.write_bytes(key)

print(f"secret.key berhasil dibuat di: {KEY_PATH}")
print("Gunakan file key yang sama untuk server_cli.py dan client_cli.py, terutama kalau client jalan di laptop berbeda.")
