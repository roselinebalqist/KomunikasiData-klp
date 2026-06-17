const form = document.getElementById("reportForm");
const statusBox = document.getElementById("statusBox");
const submitButton = document.getElementById("submitButton");
const reportList = document.getElementById("reportList");
const emptyState = document.getElementById("emptyState");
const connectionBadge = document.getElementById("connectionBadge");
const searchInput = document.getElementById("searchInput");
const filterButtons = document.querySelectorAll(".filter-chip");
const liveClock = document.getElementById("liveClock");
const tabButtons = document.querySelectorAll(".tab-button, .secondary-action");
const viewSections = document.querySelectorAll(".view-section");
const adminLoginGate = document.getElementById("adminLoginGate");
const adminContent = document.getElementById("adminContent");
const adminLoginForm = document.getElementById("adminLoginForm");
const adminPin = document.getElementById("adminPin");
const adminStatus = document.getElementById("adminStatus");
const adminLogoutButton = document.getElementById("adminLogoutButton");

let activeFilter = "all";
let isAdminAuthenticated = false;
let socket = null;

function escapeHTML(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function showView(viewId, pushHash = true) {
    const targetId = viewId === "adminView" ? "adminView" : "reportView";

    viewSections.forEach((section) => {
        section.classList.toggle("active", section.id === targetId);
    });

    document.querySelectorAll(".tab-button").forEach((button) => {
        button.classList.toggle("active", button.dataset.view === targetId);
    });

    if (pushHash) {
        window.location.hash = targetId === "adminView" ? "admin" : "report";
    }

    if (targetId === "adminView") {
        ensureAdminSession();
    }
}

tabButtons.forEach((button) => {
    button.addEventListener("click", () => showView(button.dataset.view));
});

window.addEventListener("hashchange", () => {
    showView(window.location.hash === "#admin" ? "adminView" : "reportView", false);
});

async function getKey() {
    const response = await fetch("/api/key");
    const data = await response.json();
    return data.key.trim();
}

function showStatus(type, title, message, extra = "") {
    statusBox.className = `status-box ${type}`;
    statusBox.innerHTML = `
        <strong>${escapeHTML(title)}</strong>
        <p>${escapeHTML(message)}</p>
        ${extra ? `<small>${escapeHTML(extra)}</small>` : ""}
    `;
}

function showAdminStatus(type, title, message) {
    if (!adminStatus) return;
    adminStatus.className = `status-box ${type}`;
    adminStatus.innerHTML = `
        <strong>${escapeHTML(title)}</strong>
        <p>${escapeHTML(message)}</p>
    `;
}

function syncAdminVisibility(authenticated) {
    isAdminAuthenticated = authenticated;
    adminLoginGate?.classList.toggle("hidden", authenticated);
    adminContent?.classList.toggle("hidden", !authenticated);

    const adminTab = document.querySelector('.tab-button[data-view="adminView"]');
    if (adminTab) adminTab.textContent = authenticated ? "Command Center" : "Admin Login";

    if (!authenticated) {
        if (connectionBadge) {
            connectionBadge.textContent = "Admin terkunci";
            connectionBadge.classList.remove("online");
        }
    }
}

async function ensureAdminSession() {
    try {
        const response = await fetch("/api/admin/session");
        const data = await response.json();
        syncAdminVisibility(Boolean(data.authenticated));

        if (data.authenticated) {
            await loadAdminData();
            connectAdminSocket();
        } else {
            disconnectAdminSocket();
            adminPin?.focus();
        }
    } catch (error) {
        syncAdminVisibility(false);
        showAdminStatus("error", "Gagal mengecek sesi", error.message || "Server tidak merespons.");
    }
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

if (form) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const payload = buildPayload();
        if (!payload.location || !payload.description) {
            showStatus("error", "Data belum lengkap", "Lokasi dan detail masalah wajib diisi.");
            return;
        }

        submitButton.disabled = true;
        showStatus("loading", "Mengenkripsi laporan...", "Payload sedang dienkripsi di browser sebelum dikirim ke server.");

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
}

function urgencyClass(urgency) {
    return `urgency-${String(urgency || "sedang").toLowerCase()}`;
}

function createReportCard(report) {
    const item = document.createElement("article");
    item.className = "report-card new-card";
    item.dataset.urgency = report.urgency || "Sedang";
    item.dataset.search = `${report.ticket_id} ${report.category} ${report.location} ${report.description}`.toLowerCase();

    item.innerHTML = `
        <div class="report-topline">
            <span class="ticket-id">${escapeHTML(report.ticket_id)}</span>
            <span class="urgency-pill ${urgencyClass(report.urgency)}">${escapeHTML(report.urgency)}</span>
        </div>
        <h3>${escapeHTML(report.category)}</h3>
        <p class="report-desc">${escapeHTML(report.description)}</p>
        <dl class="report-meta">
            <div><dt>Lokasi</dt><dd>${escapeHTML(report.location)}</dd></div>
            <div><dt>Prioritas</dt><dd>${escapeHTML(report.priority)}</dd></div>
            <div><dt>Status</dt><dd>${escapeHTML(report.status)}</dd></div>
            <div><dt>Waktu</dt><dd>${escapeHTML(report.received_at)}</dd></div>
        </dl>
        <div class="impact-line"><strong>Dampak:</strong> ${escapeHTML(report.impact)}</div>
    `;

    return item;
}

function renderReports(reports) {
    if (!reportList) return;
    reportList.innerHTML = "";
    reports.forEach((report) => reportList.appendChild(createReportCard(report)));
    refreshVisibility();
}

function refreshVisibility() {
    const keyword = (searchInput?.value || "").trim().toLowerCase();
    const cards = reportList?.querySelectorAll(".report-card") || [];
    let visibleCount = 0;

    cards.forEach((card) => {
        const matchesFilter = activeFilter === "all" || card.dataset.urgency === activeFilter;
        const haystack = (card.dataset.search || "").toLowerCase();
        const matchesSearch = !keyword || haystack.includes(keyword);
        const visible = matchesFilter && matchesSearch;
        card.classList.toggle("hidden", !visible);
        if (visible) visibleCount += 1;
    });

    emptyState?.classList.toggle("hidden", visibleCount !== 0);
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = String(value);
}

function updateMetricElements(stats) {
    setText("metricTotal", stats.total || 0);
    setText("metricCritical", stats.critical || 0);
    setText("metricHigh", stats.high || 0);
    setText("metricCategory", stats.top_category || "-");
    setText("metricLatest", `Terakhir masuk: ${stats.latest_time || "Belum ada laporan"}`);
    setText("sideTotal", stats.total || 0);
    setText("sideCritical", stats.critical || 0);
}

async function loadAdminData() {
    const response = await fetch("/api/reports");
    const data = await response.json();

    if (!response.ok) {
        syncAdminVisibility(false);
        showAdminStatus("error", "Akses ditolak", data.message || "Silakan login sebagai admin.");
        return;
    }

    updateMetricElements(data.stats || {});
    renderReports(data.reports || []);
}

function bumpNumber(id) {
    const element = document.getElementById(id);
    if (!element) return;
    element.textContent = String(Number(element.textContent || 0) + 1);
}

function updateStats(report) {
    bumpNumber("metricTotal");
    bumpNumber("sideTotal");

    if (report.urgency === "Kritis") {
        bumpNumber("metricCritical");
        bumpNumber("sideCritical");
    }
    if (report.urgency === "Tinggi") {
        bumpNumber("metricHigh");
    }

    const category = document.getElementById("metricCategory");
    const latest = document.getElementById("metricLatest");
    if (category) category.textContent = report.category || category.textContent;
    if (latest) latest.textContent = `Terakhir masuk: ${report.received_at || "baru saja"}`;
}

function connectAdminSocket() {
    if (socket || typeof io === "undefined") return;

    socket = io();

    socket.on("connect", () => {
        if (connectionBadge) {
            connectionBadge.textContent = "Realtime aktif";
            connectionBadge.classList.add("online");
        }
    });

    socket.on("disconnect", () => {
        if (connectionBadge) {
            connectionBadge.textContent = "Realtime terputus";
            connectionBadge.classList.remove("online");
        }
    });

    socket.on("new_report", (report) => {
        if (!isAdminAuthenticated) return;
        const item = createReportCard(report);
        reportList.prepend(item);
        updateStats(report);
        refreshVisibility();
    });
}

function disconnectAdminSocket() {
    if (socket) {
        socket.disconnect();
        socket = null;
    }
}

adminLoginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    showAdminStatus("loading", "Memeriksa PIN...", "Sebentar, admin gate lagi buka gembok.");

    try {
        const response = await fetch("/api/admin/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({pin: adminPin.value})
        });
        const data = await response.json();

        if (!response.ok || data.status !== "success") {
            throw new Error(data.message || "PIN admin salah.");
        }

        adminPin.value = "";
        syncAdminVisibility(true);
        await loadAdminData();
        connectAdminSocket();
    } catch (error) {
        syncAdminVisibility(false);
        showAdminStatus("error", "Login admin gagal", error.message || "PIN tidak valid.");
    }
});

adminLogoutButton?.addEventListener("click", async () => {
    await fetch("/api/admin/logout", {method: "POST"});
    disconnectAdminSocket();
    renderReports([]);
    updateMetricElements({total: 0, critical: 0, high: 0, top_category: "-", latest_time: "Admin terkunci"});
    syncAdminVisibility(false);
    showAdminStatus("success", "Admin dikunci", "Command Center sudah terkunci.");
});

filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
        filterButtons.forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        activeFilter = button.dataset.filter;
        refreshVisibility();
    });
});

searchInput?.addEventListener("input", refreshVisibility);

function tickClock() {
    if (liveClock) {
        liveClock.textContent = new Date().toLocaleTimeString("id-ID", {hour12: false});
    }
}

setInterval(tickClock, 1000);
tickClock();

syncAdminVisibility(false);
showView(window.location.hash === "#admin" ? "adminView" : "reportView", false);

