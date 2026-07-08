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
    document.getElementById("page-ancient").classList.add("hidden");
    document.getElementById(`page-${page}`).classList.remove("hidden");

    // Show/hide top filter bar only for upcoming
    const topFilters = document.getElementById("top-filters");
    if (topFilters) topFilters.style.display = (page === "upcoming") ? "flex" : "none";

    if (page === "upcoming") fetchUpcomingMatches();
    if (page === "analytics") fetchModels();
    if (page === "ancient") initAncientPage();
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

// ── Ancient Engine ─────────────────────────────────────────────────────────

function initAncientPage() {
    // Set default date to today
    const dateInput = document.getElementById("anc-date");
    if (dateInput && !dateInput.value) {
        dateInput.value = new Date().toISOString().split("T")[0];
    }
    // Load live matches
    fetchAncientLive();
}

async function runAncientPrediction() {
    const teamA   = document.getElementById("anc-team-a").value.trim();
    const teamB   = document.getElementById("anc-team-b").value.trim();
    const date    = document.getElementById("anc-date").value;
    const venue   = document.getElementById("anc-venue").value.trim();
    const playersA = document.getElementById("anc-players-a").value.trim();
    const playersB = document.getElementById("anc-players-b").value.trim();

    if (!teamA || !teamB) { alert("Please enter both team names."); return; }

    const loader  = document.getElementById("anc-loader");
    const results = document.getElementById("anc-results");
    loader.classList.remove("hidden");
    results.classList.add("hidden");
    results.innerHTML = "";

    try {
        const params = new URLSearchParams({ team_a: teamA, team_b: teamB });
        if (date)     params.append("date", date);
        if (venue)    params.append("venue", venue);
        if (playersA) params.append("players_a", playersA);
        if (playersB) params.append("players_b", playersB);

        const res = await fetch(`${API_URL}/api/ancient/predict?${params}`);
        if (!res.ok) throw new Error(`API error ${res.status}`);
        const data = await res.json();
        renderAncientResults(data, results);
    } catch (err) {
        results.innerHTML = `<p class="no-results" style="color:#ec4899">⚠️ ${err.message}</p>`;
    } finally {
        loader.classList.add("hidden");
        results.classList.remove("hidden");
    }
}

function renderAncientResults(data, container) {
    const consensus = data.consensus;
    const panchanga = data.panchanga || {};
    const systems   = data.systems   || [];
    const snapshot  = data.planetary_snapshot || {};

    const winnerA = consensus.team_a_prob >= 0.5;
    const probA   = Math.round(consensus.team_a_prob * 100);
    const probB   = 100 - probA;

    let html = `
    <div class="anc-consensus glass-panel">
        <div class="anc-consensus-label">⚖️ Ancient Consensus</div>
        <div class="anc-teams-row">
            <div class="anc-team ${winnerA ? 'anc-winner' : ''}">
                <div class="anc-logo">${getInitials(data.team_a)}</div>
                <div class="anc-name">${data.team_a}</div>
                <div class="anc-prob" style="color:var(--primary)">${probA}%</div>
            </div>
            <div class="anc-vs">VS</div>
            <div class="anc-team ${!winnerA ? 'anc-winner' : ''}">
                <div class="anc-logo">${getInitials(data.team_b)}</div>
                <div class="anc-name">${data.team_b}</div>
                <div class="anc-prob" style="color:var(--secondary)">${probB}%</div>
            </div>
        </div>
        <div class="anc-bar-wrap">
            <div class="anc-bar-fill" style="width:${probA}%"></div>
        </div>
        <div class="anc-winner-text">🏆 Predicted Winner: <strong>${consensus.predicted_winner}</strong></div>
    </div>

    <div class="panchanga-card glass-panel">
        <div class="panch-title">📅 Panchanga for ${data.match_date}</div>
        <div class="panch-grid">
            <div class="panch-item"><span>Tithi</span><strong>${panchanga.tithi}</strong></div>
            <div class="panch-item"><span>Nakshatra</span><strong>${panchanga.nakshatra || 'N/A'}</strong></div>
            <div class="panch-item"><span>Vara</span><strong>${panchanga.vara}</strong></div>
            <div class="panch-item"><span>Vara Lord</span><strong>${panchanga.vara_lord}</strong></div>
        </div>
    </div>

    <h3 class="section-title" style="margin-top:1.5rem">📊 All 4 Ancient Systems</h3>
    <div class="anc-systems-grid">
        ${systems.map(s => `
        <div class="anc-system-card glass-panel">
            <div class="anc-sys-header">
                <span class="anc-sys-emoji">${s.emoji}</span>
                <span class="anc-sys-name">${s.system}</span>
                <span class="anc-sys-winner ${s.predicted_winner === data.team_a ? 'winner-a' : 'winner-b'}">${s.predicted_winner}</span>
            </div>
            <div class="anc-sys-bar-wrap">
                <span class="bar-label-l">${data.team_a} ${Math.round(s.team_a_prob*100)}%</span>
                <div class="anc-sys-bar">
                    <div class="anc-sys-fill" style="width:${Math.round(s.team_a_prob*100)}%"></div>
                </div>
                <span class="bar-label-r">${Math.round(s.team_b_prob*100)}% ${data.team_b}</span>
            </div>
            <p class="anc-sys-explanation">${s.explanation}</p>
        </div>`).join("")}
    </div>

    <h3 class="section-title" style="margin-top:1.5rem">🪐 Planetary Snapshot</h3>
    <div class="planet-grid">
        ${Object.entries(snapshot).map(([name, info]) => `
        <div class="planet-card ${info.exalted ? 'exalted' : info.retrograde ? 'retrograde' : ''}">
            <div class="planet-name">${name}</div>
            <div class="planet-sign">Sign ${info.sign}</div>
            <div class="planet-state">
                ${info.exalted ? '✨ Exalted' : info.retrograde ? '↩ Retrograde' : '● Direct'}
            </div>
        </div>`).join("")}
    </div>`;

    container.innerHTML = html;
}

async function fetchAncientLive() {
    const liveLoader = document.getElementById("anc-live-loader");
    const liveGrid   = document.getElementById("anc-live-grid");
    if (!liveLoader || !liveGrid) return;

    liveLoader.classList.remove("hidden");
    liveGrid.classList.add("hidden");
    liveGrid.innerHTML = "";

    try {
        const res = await fetch(`${API_URL}/api/ancient/live`);
        if (!res.ok) throw new Error(`API error ${res.status}`);
        const data = await res.json();

        if (!data.predictions.length) {
            liveGrid.innerHTML = `<p class="no-results">No live matches found from CricAPI right now.</p>`;
        } else {
            data.predictions.forEach(item => {
                const card = createAncientLiveCard(item);
                if (card) liveGrid.appendChild(card);
            });
        }
    } catch (err) {
        liveGrid.innerHTML = `<p class="no-results" style="color:#ec4899">⚠️ ${err.message}</p>`;
    } finally {
        liveLoader.classList.add("hidden");
        liveGrid.classList.remove("hidden");
    }
}

function createAncientLiveCard(item) {
    const match = item.match;
    const pred  = item.ancient_prediction;
    const teams = match.teams || [];
    if (!teams.length) return null;

    const consensus = pred.consensus;
    const probA = Math.round(consensus.team_a_prob * 100);
    const probB = 100 - probA;

    const card = document.createElement("div");
    card.className = "match-card ancient-live-card";
    card.innerHTML = `
        <div class="match-meta">
            <span class="format-badge ancient-badge">Ancient Reading</span>
            <span class="match-date">${match.date || ''}</span>
        </div>
        <div class="match-teams">
            <div class="team ${consensus.team_a_prob >= 0.5 ? 'predicted-winner' : ''}">
                <div class="team-logo">${getInitials(teams[0] || 'A')}</div>
                <div class="team-name">${teams[0] || 'Team A'}</div>
                <div class="team-prob">${probA}%</div>
            </div>
            <div class="vs-badge" style="background:rgba(168,85,247,0.15);color:#a855f7">VS</div>
            <div class="team ${consensus.team_b_prob > consensus.team_a_prob ? 'predicted-winner' : ''}">
                <div class="team-logo">${getInitials(teams[1] || 'B')}</div>
                <div class="team-name">${teams[1] || 'Team B'}</div>
                <div class="team-prob">${probB}%</div>
            </div>
        </div>
        <div class="venue-info"><i class="fas fa-map-marker-alt"></i> ${match.venue || 'Venue unknown'}</div>
        <div class="prediction-section" style="background:rgba(168,85,247,0.08);border:1px solid rgba(168,85,247,0.2)">
            <div class="pred-title" style="color:#a855f7">🔮 Ancient Consensus</div>
            <div class="pred-teams">
                <span style="color:#818cf8">${teams[0]} ${probA}%</span>
                <span style="color:#c084fc">${probB}% ${teams[1]}</span>
            </div>
            <div class="pred-bar-container" style="background:#c084fc">
                <div class="pred-bar-fill" style="width:${probA}%;background:#818cf8"></div>
            </div>
            <div class="pred-winner-label">🏆 Winner: <strong style="color:#a855f7">${consensus.predicted_winner}</strong></div>
        </div>`;
    return card;
}
