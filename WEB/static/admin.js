const socket = io();
const reportList = document.getElementById("reportList");
const emptyState = document.getElementById("emptyState");
const connectionBadge = document.getElementById("connectionBadge");
const searchInput = document.getElementById("searchInput");
const filterButtons = document.querySelectorAll(".filter-chip");
const liveClock = document.getElementById("liveClock");

let activeFilter = "all";

function escapeHTML(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
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

function refreshVisibility() {
    const keyword = searchInput.value.trim().toLowerCase();
    const cards = reportList.querySelectorAll(".report-card");
    let visibleCount = 0;

    cards.forEach((card) => {
        const matchesFilter = activeFilter === "all" || card.dataset.urgency === activeFilter;
        const haystack = (card.dataset.search || "").toLowerCase();
        const matchesSearch = !keyword || haystack.includes(keyword);
        const visible = matchesFilter && matchesSearch;
        card.classList.toggle("hidden", !visible);
        if (visible) visibleCount += 1;
    });

    emptyState.classList.toggle("hidden", visibleCount !== 0);
}

function updateStats(report) {
    const total = document.getElementById("metricTotal");
    const critical = document.getElementById("metricCritical");
    const high = document.getElementById("metricHigh");
    const category = document.getElementById("metricCategory");

    total.textContent = String(Number(total.textContent || 0) + 1);
    if (report.urgency === "Kritis") critical.textContent = String(Number(critical.textContent || 0) + 1);
    if (report.urgency === "Tinggi") high.textContent = String(Number(high.textContent || 0) + 1);
    category.textContent = report.category || category.textContent;
}

socket.on("connect", () => {
    connectionBadge.textContent = "Realtime aktif";
    connectionBadge.classList.add("online");
});

socket.on("disconnect", () => {
    connectionBadge.textContent = "Realtime terputus";
    connectionBadge.classList.remove("online");
});

socket.on("new_report", (report) => {
    const item = createReportCard(report);
    reportList.prepend(item);
    updateStats(report);
    refreshVisibility();
});

filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
        filterButtons.forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        activeFilter = button.dataset.filter;
        refreshVisibility();
    });
});

searchInput.addEventListener("input", refreshVisibility);

function tickClock() {
    liveClock.textContent = new Date().toLocaleTimeString("id-ID", {hour12: false});
}

setInterval(tickClock, 1000);
tickClock();
refreshVisibility();
