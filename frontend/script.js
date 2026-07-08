const API_URL = "http://127.0.0.1:8000";

let currentFilters = { match_type: "all", gender: "all", venue: "" };
let currentPage = "upcoming";

document.addEventListener("DOMContentLoaded", () => {
    setupFilters();
    setupNav();
    showPage("upcoming");
});

// ── Navigation ─────────────────────────────────────────────────────────────
function setupNav() {
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
            item.classList.add("active");
            showPage(item.dataset.page);
        });
    });
}

function showPage(page) {
    currentPage = page;
    document.getElementById("page-upcoming").classList.add("hidden");
    document.getElementById("page-analytics").classList.add("hidden");
    document.getElementById(`page-${page}`).classList.remove("hidden");
    
    if (page === "upcoming") fetchUpcomingMatches();
    if (page === "analytics") fetchModels();
}

// ── Filters ────────────────────────────────────────────────────────────────
function setupFilters() {
    document.querySelectorAll("#match-type-filters .filter-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll("#match-type-filters .filter-btn").forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            currentFilters.match_type = e.target.dataset.filter;
            fetchUpcomingMatches();
        });
    });

    document.querySelectorAll("#gender-filters .filter-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll("#gender-filters .filter-btn").forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            currentFilters.gender = e.target.dataset.filter;
            fetchUpcomingMatches();
        });
    });

    const searchInput = document.getElementById("venue-search");
    if (searchInput) {
        searchInput.addEventListener("keyup", (e) => {
            currentFilters.venue = e.target.value;
            if (e.key === "Enter" || currentFilters.venue.length === 0) fetchUpcomingMatches();
        });
    }
}

// ── Upcoming Matches ───────────────────────────────────────────────────────
async function fetchUpcomingMatches() {
    const loader = document.getElementById("loader");
    const grid = document.getElementById("matches-grid");
    loader.classList.remove("hidden");
    grid.classList.add("hidden");
    grid.innerHTML = "";

    try {
        const params = new URLSearchParams();
        if (currentFilters.match_type !== "all") params.append("match_type", currentFilters.match_type);
        if (currentFilters.gender !== "all") params.append("gender", currentFilters.gender);
        if (currentFilters.venue) params.append("venue", currentFilters.venue);

        const res = await fetch(`${API_URL}/api/matches/upcoming?${params}`);
        if (!res.ok) throw new Error(`API error ${res.status}`);
        const data = await res.json();

        if (!data.matches.length) {
            grid.innerHTML = `<p class="no-results">No upcoming matches found for these filters.</p>`;
        } else {
            data.matches.forEach(m => grid.appendChild(createMatchCard(m)));
        }
    } catch (err) {
        grid.innerHTML = `<p class="no-results" style="color:#ec4899">⚠️ Could not reach API: ${err.message}<br><small>Make sure start_backend.bat is running.</small></p>`;
    } finally {
        loader.classList.add("hidden");
        grid.classList.remove("hidden");
    }
}

function getInitials(name) {
    return name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
}

function createMatchCard(match) {
    const card = document.createElement("div");
    card.className = "match-card";

    const dateStr = new Date(match.date).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const pred = match.prediction || {};
    const hasError = !!pred.error;

    // Determine win probs for both teams
    let probA = 50, probB = 50, winner = null;
    if (!hasError && pred.probability != null) {
        const raw = Math.round(pred.probability * 100);
        if (pred.predicted_winner === match.team_a || pred.winner === match.team_a) {
            probA = raw; probB = 100 - raw; winner = match.team_a;
        } else {
            probB = raw; probA = 100 - raw; winner = match.team_b;
        }
    }

    const modelLabel = pred.model_used
        ? pred.model_used.includes("xgboost")
            ? (pred.model_used.includes("astronomy") ? "XGBoost + Astro" : "XGBoost")
            : "Logistic Regression"
        : "AI Model";

    const genderLabel = match.gender === "female" ? "WOMEN" : "MEN";
    const winnerClass = !hasError ? (probA > probB ? "team-a-win" : "team-b-win") : "";

    card.innerHTML = `
        <div class="match-meta">
            <span class="format-badge">${match.match_type} · ${genderLabel}</span>
            <span class="match-date">${dateStr}</span>
        </div>
        <div class="match-teams ${winnerClass}">
            <div class="team ${!hasError && probA > probB ? 'predicted-winner' : ''}">
                <div class="team-logo">${getInitials(match.team_a)}</div>
                <div class="team-name">${match.team_a}</div>
                ${!hasError ? `<div class="team-prob">${probA}%</div>` : ''}
            </div>
            <div class="vs-badge">VS</div>
            <div class="team ${!hasError && probB > probA ? 'predicted-winner' : ''}">
                <div class="team-logo">${getInitials(match.team_b)}</div>
                <div class="team-name">${match.team_b}</div>
                ${!hasError ? `<div class="team-prob">${probB}%</div>` : ''}
            </div>
        </div>
        <div class="venue-info"><i class="fas fa-map-marker-alt"></i> ${match.venue}</div>
        <div class="prediction-section">
            <div class="pred-title"><i class="fas fa-robot"></i> GlobalPulse AI · ${modelLabel}</div>
            ${hasError
                ? `<div class="pred-error">⚠️ Prediction unavailable</div>`
                : `<div class="pred-teams">
                    <span style="color:var(--primary)">${match.team_a} ${probA}%</span>
                    <span style="color:var(--secondary)">${probB}% ${match.team_b}</span>
                   </div>
                   <div class="pred-bar-container">
                       <div class="pred-bar-fill" style="width:${probA}%"></div>
                   </div>
                   <div class="pred-winner-label">Predicted Winner: <strong>${winner}</strong></div>`
            }
        </div>`;

    return card;
}

// ── AI Analytics Page ──────────────────────────────────────────────────────
async function fetchModels() {
    const container = document.getElementById("analytics-content");
    container.innerHTML = `<div class="loader-container"><div class="spinner"></div><p>Loading model registry...</p></div>`;

    try {
        const res = await fetch(`${API_URL}/api/models`);
        if (!res.ok) throw new Error(`API error ${res.status}`);
        const data = await res.json();
        renderAnalytics(data.models);
    } catch (err) {
        container.innerHTML = `<p class="no-results" style="color:#ec4899">⚠️ ${err.message}</p>`;
    }
}

function renderAnalytics(models) {
    const container = document.getElementById("analytics-content");
    if (!models.length) {
        container.innerHTML = `<p class="no-results">No models registered yet. Run the pipeline first.</p>`;
        return;
    }

    const champion = models.find(m => m.is_champion);
    
    let html = `
        <div class="analytics-header">
            <div class="champion-card glass-panel">
                <div class="champ-label">🏆 Champion Model</div>
                <div class="champ-name">${champion ? algoLabel(champion.algorithm) : 'None'}</div>
                <div class="champ-family">${champion ? familyLabel(champion.feature_family) : ''}</div>
                <div class="champ-meta">Trained on data up to ${champion ? champion.train_years : 'N/A'}</div>
            </div>
        </div>
        <h3 class="section-title">All Trained Models</h3>
        <div class="models-table-wrap">
            <table class="models-table">
                <thead>
                    <tr>
                        <th>Algorithm</th>
                        <th>Feature Set</th>
                        <th>Training Period</th>
                        <th>Test Year</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${models.map(m => `
                    <tr class="${m.is_champion ? 'champion-row' : ''}">
                        <td><span class="algo-badge ${m.algorithm}">${algoLabel(m.algorithm)}</span></td>
                        <td>${familyLabel(m.feature_family)}</td>
                        <td>${m.train_years}</td>
                        <td>${m.test_year}</td>
                        <td>
                            ${m.is_champion ? '<span class="badge-champion">Champion</span>' : ''}
                            ${m.artifact_ready ? '<span class="badge-ready">✓ Loaded</span>' : '<span class="badge-missing">✗ Missing</span>'}
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>
        </div>
        <div class="accuracy-note glass-panel">
            <h4>📊 How Predictions Work</h4>
            <p>The Champion XGBoost + Astronomy model uses <strong>11 features per match</strong>:</p>
            <ul>
                <li><strong>Statistics (8 features):</strong> Team A/B win rates (last 5, 10, all-time), Head-to-Head win %, Venue win %, Elo ratings</li>
                <li><strong>Astronomy (3+ features):</strong> Sun/Moon/Mars planetary positions, Tithi, Nakshatra from Swiss Ephemeris</li>
            </ul>
            <p>All stats are computed from <strong>16,000+ real historical cricket matches</strong> in the local database.</p>
        </div>`;

    container.innerHTML = html;
}

function algoLabel(algo) {
    const map = { xgboost: "XGBoost", logistic_regression: "Logistic Regression" };
    return map[algo] || algo;
}

function familyLabel(family) {
    if (!family) return "Unknown";
    if (family.includes("astronomy")) return "Statistics + Astronomy";
    return "Statistics";
}
