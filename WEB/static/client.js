const form = document.getElementById("reportForm");
const statusBox = document.getElementById("statusBox");
const submitButton = document.getElementById("submitButton");

async function getKey() {
    const response = await fetch("/api/key");
    const data = await response.json();
    return data.key.trim();
}

function showStatus(type, title, message, extra = "") {
    statusBox.className = `status-box ${type}`;
    statusBox.innerHTML = `
        <strong>${title}</strong>
        <p>${message}</p>
        ${extra ? `<small>${extra}</small>` : ""}
    `;
}

function buildPayload() {
    return {
        source: "Web",
        category: document.getElementById("category").value,
        urgency: document.getElementById("urgency").value,
        location: document.getElementById("location").value.trim(),
        description: document.getElementById("description").value.trim(),
        impact: document.getElementById("impact").value.trim() || "Belum dijelaskan",
        contact_code: document.getElementById("contactCode").value.trim() || "Anonim penuh",
        created_at_client: new Date().toLocaleString("id-ID")
    };
}

function encryptPayload(key, payload) {
    const secret = new fernet.Secret(key);
    const iv = Array.from(crypto.getRandomValues(new Uint8Array(16)));
    const token = new fernet.Token({
        secret,
        time: Date.now(),
        iv
    });
    return token.encode(JSON.stringify(payload));
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = buildPayload();
    if (!payload.location || !payload.description) {
        showStatus("error", "Data belum lengkap", "Lokasi dan detail masalah wajib diisi.");
        return;
    }

    submitButton.disabled = true;
    showStatus("loading", "Mengenkripsi laporan...", "Payload sedang dienkripsi di sisi browser sebelum dikirim ke server.");

    try {
        if (typeof fernet === "undefined") {
            throw new Error("Library Fernet browser gagal dimuat. Pastikan koneksi internet aktif untuk CDN.");
        }

        const key = await getKey();
        const encryptedReport = encryptPayload(key, payload);

        const response = await fetch("/api/report", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({encrypted_report: encryptedReport})
        });

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Server menolak laporan.");
        }

        showStatus(
            "success",
            "Laporan berhasil dikirim",
            result.message,
            `Ticket ID: ${result.ticket_id} • Prioritas: ${result.priority} • Diterima: ${result.received_at}`
        );

        form.reset();
        document.getElementById("urgency").value = "Sedang";
    } catch (error) {
        showStatus("error", "Gagal mengirim laporan", error.message || "Terjadi kesalahan saat mengirim data.");
        console.error(error);
    } finally {
        submitButton.disabled = false;
    }
});
