// ─── State ────────────────────────────────────────────────────────────────
let restaurants = [];

// ─── Helpers ──────────────────────────────────────────────────────────────

async function api(path, options = {}) {
    const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

function formatTime(ts) {
    if (!ts) return "";
    const d = new Date(ts.replace(" ", "T") + "Z");
    return d.toLocaleString();
}

// ─── Render ───────────────────────────────────────────────────────────────

function renderRestaurants(list) {
    const container = document.getElementById("restaurants");
    restaurants = list;

    if (list.length === 0) {
        container.innerHTML = `<p class="empty-state">No restaurants yet. Add your first one above!</p>`;
        return;
    }

    container.innerHTML = list.map(r => `
        <div class="restaurant-item" data-id="${r.id}">
            <div class="restaurant-info">
                <div class="restaurant-name">${escapeHtml(r.name)}</div>
                <div class="restaurant-url">${escapeHtml(r.url)}</div>
            </div>
            <div class="restaurant-actions">
                <button class="btn-small" onclick="openRestaurant(${r.id}, '${escapeHtml(r.url)}')">Open</button>
                <button class="btn-small" onclick="checkOne(${r.id}, '${escapeHtml(r.name)}')">Check</button>
                <button class="btn-small btn-danger" onclick="deleteRestaurant(${r.id})">✕</button>
            </div>
        </div>
    `).join("");
}

function renderScreenshots(results) {
    const section = document.getElementById("gallery-section");
    const container = document.getElementById("screenshots");
    const count = document.getElementById("gallery-count");

    if (!results || results.length === 0) {
        section.style.display = "none";
        return;
    }

    section.style.display = "block";
    count.textContent = `(${results.length})`;

    container.innerHTML = results.map(s => {
        const imgTag = s.screenshot_path && s.status === "success"
            ? `<img src="/screenshots/${encodeURIComponent(s.screenshot_path.split('/').pop())}" alt="${escapeHtml(s.restaurant_name)}">`
            : `<div class="screenshot-error">Failed: ${escapeHtml(s.status)}</div>`;

        return `
            <div class="screenshot-card">
                ${imgTag}
                <div class="screenshot-footer">
                    <span class="screenshot-restaurant">${escapeHtml(s.restaurant_name)}</span>
                    <span class="screenshot-time">${formatTime(s.timestamp)}</span>
                </div>
            </div>
        `;
    }).join("");
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// ─── Actions ──────────────────────────────────────────────────────────────

async function loadRestaurants() {
    try {
        const data = await api("/api/restaurants");
        renderRestaurants(data);
    } catch (err) {
        console.error("Failed to load restaurants:", err);
    }
}

document.getElementById("add-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("name").value.trim();
    const url = document.getElementById("url").value.trim();
    const errorEl = document.getElementById("form-error");
    errorEl.textContent = "";

    if (!name || !url) return;

    try {
        const data = await api("/api/restaurants", {
            method: "POST",
            body: JSON.stringify({ name, url })
        });
        renderRestaurants([...restaurants, data]);
        document.getElementById("add-form").reset();
    } catch (err) {
        errorEl.textContent = err.message;
    }
});

document.getElementById("check-all").addEventListener("click", async () => {
    const btn = document.getElementById("check-all");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Checking all...';

    const container = document.getElementById("screenshots");
    container.innerHTML = '<div class="loading"><span class="spinner"></span> Capturing waitlists...</div>';
    document.getElementById("gallery-section").style.display = "block";

    try {
        const results = await api("/api/check-all", { method: "POST" });
        renderScreenshots(results);
        btn.disabled = false;
        btn.innerHTML = '📸 Check All Waitlists';
    } catch (err) {
        container.innerHTML = `<div class="screenshot-error">Error: ${escapeHtml(err.message)}</div>`;
        btn.disabled = false;
        btn.innerHTML = '📸 Check All Waitlists';
    }
});

async function checkOne(id, name) {
    try {
        const result = await api(`/api/restaurants/${id}/check`, { method: "POST" });
        
        // Refresh screenshots for this restaurant
        const screenshots = await api(`/api/restaurants/${id}/screenshots`);
        renderScreenshots([{ ...result, restaurant_name: name }, ...screenshots.slice(0, 10)]);
    } catch (err) {
        alert(`Error checking waitlist: ${err.message}`);
    }
}

async function openRestaurant(id, url) {
    window.open(url, "_blank");
}

async function deleteRestaurant(id) {
    if (!confirm("Remove this restaurant from your watchlist?")) return;
    try {
        await api(`/api/restaurants/${id}`, { method: "DELETE" });
        renderRestaurants(restaurants.filter(r => r.id !== id));
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
}

// ─── Init ─────────────────────────────────────────────────────────────────

loadRestaurants();
