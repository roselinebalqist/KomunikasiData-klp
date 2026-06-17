# KomunikasiData-klp

# Secure Campus Report - Chatroom Laporan Fasilitas Kampus Anonim Terenkripsi

Project ini adalah pengembangan dari chatroom laporan anonim menjadi sistem pelaporan insiden fasilitas kampus yang lebih profesional. Sistem ini menyiapkan versi CLI, versi web-based, memakai komunikasi client-server, mendukung multi-user, dan juga pesan dikirim dalam bentuk terenkripsi.

## Fitur Utama

- **CLI TCP multithreading**: beberapa client bisa mengirim laporan ke server yang sama.
- **Web-based single URL**: form laporan dan Command Center admin tetap berada dalam satu alamat web yang sama.
- **Tampilan terpisah dalam satu halaman**: user hanya melihat Form Pengaduan, sedangkan Command Center baru muncul setelah admin login dengan PIN.
- **Form laporan profesional**: kategori, lokasi, urgensi, detail, dampak, dan kode pelapor opsional.
- **Admin Command Center terkunci**: statistik, filter urgensi, pencarian laporan, antrean ticket, dan realtime feed hanya bisa dilihat setelah login admin.
- **Enkripsi Fernet**: payload laporan dienkripsi di sisi client, lalu didekripsi di server.
- **Ticket ID otomatis**: setiap laporan mendapat kode seperti `INC-260610-ABC123`.
- **JSON log**: laporan CLI dan web disimpan ke file `.jsonl` agar bisa ditunjukkan sebagai bukti data diterima server.

---

## 1. Cara Menjalankan Versi CLI

### Install library

```bash
cd cli
pip install -r requirements.txt
python generate_key.py
```

### Jalankan server CLI

```bash
python server_cli.py
```

Server akan listening di `0.0.0.0:5000`, jadi bisa diakses dari laptop lain selama satu jaringan dan firewall mengizinkan.

### Jalankan client CLI

Di terminal lain:

```bash
python client_cli.py
```

Isi alamat server:

- Kalau satu laptop: `127.0.0.1`
- Kalau beda laptop: isi IP laptop server, contoh `192.168.1.10`

> Catatan: kalau client beda laptop, copy file `secret.key` dari folder CLI server ke folder CLI client supaya enkripsi dan dekripsi cocok.

---

## 2. Cara Menjalankan Versi Web-Based

### Install library

```bash
cd web
pip install -r requirements.txt
```

### Jalankan web server

```bash
python app.py
```

Server berjalan di satu alamat utama:

```text
http://127.0.0.1:8000/
```

Kalau mau dibuka dari laptop lain dalam jaringan yang sama, gunakan IP laptop server:

```text
http://IP-SERVER:8000/
```

### Login admin di web

Command Center sekarang dikunci agar user biasa tidak bisa melihat daftar laporan. Masih satu alamat web, tapi admin harus login dulu menggunakan password admin.

- PIN admin default: `admin123`
- Kalau ingin mengganti PIN, jalankan server dengan environment variable `ADMIN_PIN`.

Contoh PowerShell:

```powershell
$env:ADMIN_PIN="123456"
python app.py
```

Contoh CMD:

```cmd
set ADMIN_PIN=123456
python app.py
```

### Cara demo web

1. Buka `http://127.0.0.1:8000/`.
2. User langsung melihat **Form Pengaduan** tanpa panel status tambahan.
3. Isi laporan, lalu klik **Kirim laporan terenkripsi**.
4. Klik **Admin Login** di bagian atas, masukkan PIN admin, lalu halaman yang sama berubah menjadi **Command Center**.
5. Laporan baru akan muncul di antrean admin secara real-time tanpa membuka URL lain.

> Route `/admin` tetap tersedia sebagai redirect kompatibilitas, tapi admin sebenarnya tetap berada di alamat utama melalui mode admin yang dikunci PIN.

Health check API:

```text
http://127.0.0.1:8000/api/health
```

---

## 3. Alur Komunikasi Data

### Versi CLI

1. Client mengisi kategori, lokasi, urgensi, detail, dampak, dan kode pelapor opsional.
2. Data disusun menjadi JSON payload.
3. Payload dienkripsi dengan Fernet menggunakan `secret.key`.
4. Client mengirim data terenkripsi melalui TCP socket ke server.
5. Server menerima data melalui thread khusus untuk tiap client.
6. Server mendekripsi payload, memvalidasi format JSON, lalu membuat ticket ID.
7. Server menyimpan laporan ke `reports_cli.jsonl`.
8. Server mengirim balasan terenkripsi ke client berisi status, ticket ID, dan prioritas.

### Versi Web-Based

1. Browser menampilkan satu aplikasi web di alamat `/`.
2. User biasa hanya melihat **Form Pengaduan**.
3. User mengisi kategori, lokasi, urgensi, detail masalah, dampak, dan kode pelapor opsional.
4. Browser mengambil demo key dari `/api/key`.
5. Browser mengenkripsi JSON payload memakai Fernet.
6. Browser mengirim payload terenkripsi ke `/api/report` dengan HTTP POST.
7. Server Flask mendekripsi payload, membuat ticket ID, menentukan prioritas, dan menyimpan log ke `reports_web.jsonl`.
8. Admin membuka **Admin Login** di alamat yang sama dan memasukkan PIN.
9. Setelah session admin valid, Command Center memuat `/api/reports` dan menerima event `new_report` melalui Socket.IO secara real-time.

---

## 4. Struktur Project

```text
chatroom_laporan_anonim_terenkripsi/
├── README.md
├── cli/
│   ├── client_cli.py
│   ├── generate_key.py
│   ├── requirements.txt
│   └── server_cli.py
└── web/
    ├── app.py
    ├── requirements.txt
    ├── static/
    │   ├── app.js
    │   └── style.css
    └── templates/
        └── app.html
```

---

## 5. Catatan Keamanan

Project ini dibuat untuk pembelajaran Komunikasi Data. Enkripsi Fernet dipakai agar proses enkripsi-dekripsi bisa ditunjukkan dengan jelas pada kode. Untuk sistem produksi nyata, distribusi key tidak boleh diberikan langsung lewat endpoint `/api/key`; gunakan HTTPS/TLS, autentikasi admin, database sungguhan, dan mekanisme key exchange yang lebih aman.
