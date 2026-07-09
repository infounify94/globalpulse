const API_URL = "";

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
    const shadowPage = document.getElementById("page-shadow");
    if(shadowPage) shadowPage.classList.add("hidden");
    
    document.getElementById(`page-${page}`).classList.remove("hidden");

    // Show/hide top filter bar only for upcoming
    const topFilters = document.getElementById("top-filters");
    if (topFilters) topFilters.style.display = (page === "upcoming") ? "flex" : "none";

    if (page === "upcoming") fetchUpcomingMatches();
    if (page === "analytics") fetchModels();
    if (page === "ancient") initAncientPage();
    if (page === "shadow") fetchShadowMode();
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

    const champion = models.find(m => m.is_champion) || [...models].sort((a,b) => (b.accuracy || 0) - (a.accuracy || 0))[0];
    
    // Sort models by accuracy descending for the leaderboard
    const sortedModels = [...models].sort((a, b) => (b.accuracy || 0) - (a.accuracy || 0));

    let html = `
        <div class="analytics-header">
            <div class="champion-card glass-panel" style="width: 100%;">
                <div class="champ-label">🏆 Ablation Leaderboard Champion</div>
                <div class="champ-name">${champion ? algoLabel(champion.algorithm) : 'None'}</div>
                <div class="champ-family" style="font-size:1.2rem; margin-top:0.5rem; color:var(--primary)">
                    ${champion ? champion.feature_family : ''}
                </div>
                <div class="champ-meta">
                    Test Accuracy: <strong>${champion && champion.accuracy ? (champion.accuracy*100).toFixed(2) + '%' : 'N/A'}</strong> 
                    | Trained on: ${champion ? champion.train_years : 'N/A'}
                </div>
            </div>
        </div>

        <h3 class="section-title">Ablation Study Leaderboard</h3>
        <div class="models-table-wrap glass-panel" style="padding: 1rem; margin-bottom: 2rem;">
            <table class="models-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Algorithm</th>
                        <th>Feature Set (Ablation Variant)</th>
                        <th>Accuracy</th>
                        <th>Brier Score</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${sortedModels.map((m, idx) => `
                    <tr class="${idx === 0 ? 'champion-row' : ''}">
                        <td>#${idx + 1}</td>
                        <td>${algoLabel(m.algorithm)}</td>
                        <td style="text-transform: capitalize;">${m.feature_family.replace(/_/g, ' ')}</td>
                        <td style="font-weight: bold; color: ${idx===0 ? 'var(--primary)' : 'inherit'}">
                            ${m.accuracy ? (m.accuracy * 100).toFixed(2) + '%' : 'N/A'}
                        </td>
                        <td>${m.brier_score ? m.brier_score.toFixed(4) : 'N/A'}</td>
                        <td>
                            ${idx === 0 ? '<span class="badge-champion">Top Model</span>' : ''}
                            ${m.artifact_ready ? '<span class="badge-ready">✓ Loaded</span>' : '<span class="badge-missing">✗ Missing</span>'}
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>
        </div>

        <h3 class="section-title">📅 Season-by-Season Stability</h3>
        <div class="models-table-wrap glass-panel" style="padding: 1rem; margin-bottom: 2rem;">
            <p style="margin-bottom: 1rem; color:#9ca3af; font-size: 0.9rem;">
                Tracking the Champion model's accuracy across individual test years to prove long-term consistency.
            </p>
            <table class="models-table">
                <thead>
                    <tr>
                        <th>Season (Year)</th>
                        <th>Test Accuracy</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>Log Loss</th>
                        <th>ECE (Calibration)</th>
                    </tr>
                </thead>
                <tbody>
                    ${champion && champion.season_metrics && Object.keys(champion.season_metrics).length > 0 ? 
                        Object.entries(champion.season_metrics).sort().map(([year, met]) => `
                        <tr>
                            <td style="font-weight: bold; color:var(--primary)">${year}</td>
                            <td>${met.accuracy ? (met.accuracy * 100).toFixed(2) + '%' : 'N/A'}</td>
                            <td>${met.precision ? (met.precision * 100).toFixed(2) + '%' : 'N/A'}</td>
                            <td>${met.recall ? (met.recall * 100).toFixed(2) + '%' : 'N/A'}</td>
                            <td>${met.log_loss ? met.log_loss.toFixed(4) : 'N/A'}</td>
                            <td>${met.calibration_error_ece ? met.calibration_error_ece.toFixed(4) : 'N/A'}</td>
                        </tr>`).join('') 
                    : '<tr><td colspan="6" style="text-align:center">No season data available.</td></tr>'}
                </tbody>
            </table>
        </div>

        <h3 class="section-title">🔍 Feature Importance (SHAP)</h3>
        <div class="models-table-wrap glass-panel" style="padding: 1rem;">
            <p style="margin-bottom: 1rem; color:#9ca3af; font-size: 0.9rem;">
                Shows the most predictive features across the top model. Let the ML engine objectively score Ancient vs Statistical predictors.
            </p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                <!-- Top Model Features -->
                <div>
                    <h4 style="margin-bottom: 0.5rem; color:var(--primary)">Top Model (${champion ? champion.feature_family.replace(/_/g, ' ') : ''})</h4>
                    <div style="background:rgba(0,0,0,0.2); padding:1rem; border-radius:8px;">
                        ${champion && champion.feature_importance ? 
                            Object.entries(champion.feature_importance)
                            .slice(0, 15) // top 15
                            .map(([feat, score]) => `
                                <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.85rem;">
                                    <span style="color:#d1d5db">${feat}</span>
                                    <span style="color:var(--primary)">${score.toFixed(4)}</span>
                                </div>
                                <div class="pred-bar-container" style="height:4px; margin-bottom:0.8rem; background:rgba(255,255,255,0.1)">
                                    <div class="pred-bar-fill" style="width:${Math.min(100, score*100)}%; background:var(--primary)"></div>
                                </div>
                            `).join('') : '<p>No feature importance data available.</p>'
                        }
                    </div>
                </div>
                
                <!-- Interpretation Note -->
                <div>
                    <h4 style="margin-bottom: 0.5rem; color:#a855f7">Objective Analysis</h4>
                    <ul style="color:#d1d5db; font-size:0.9rem; line-height:1.6; list-style:disc; margin-left:1.5rem;">
                        <li>If <strong style="color:var(--secondary)">statistics</strong> (win_pct, elo) dominate, it confirms traditional data science.</li>
                        <li>If <strong style="color:var(--primary)">astronomy</strong> (moon_phase, tithi) rank highly, it proves non-linear correlations exist in planetary cycles.</li>
                        <li>If <strong style="color:#f43f5e">vedic/babylonian</strong> (exaltation, retrogrades) appear in the top 10, it implies ancient omens mathematically correlate to match outcomes in XGBoost.</li>
                    </ul>
                </div>
            </div>
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

// ── Shadow Mode Page ───────────────────────────────────────────────────────
async function fetchShadowMode() {
    const loader = document.getElementById("shadow-loader");
    const grid = document.getElementById("shadow-predictions-grid");
    
    loader.classList.remove("hidden");
    grid.classList.add("hidden");
    grid.innerHTML = "";

    try {
        // Fetch Metrics
        const metricsRes = await fetch(`${API_URL}/api/shadow_metrics`);
        if (metricsRes.ok) {
            const m = await metricsRes.json();
            if (m.overall_accuracy !== undefined) {
                document.getElementById("sm-acc-50").innerText = (m.rolling_50_accuracy * 100).toFixed(1) + "%";
                document.getElementById("sm-brier").innerText = m.brier_score.toFixed(3);
                document.getElementById("sm-roi").innerText = (m.roi * 100).toFixed(1) + "%";
            }
        }

        // Fetch Predictions
        const res = await fetch(`${API_URL}/api/shadow_predictions`);
        if (!res.ok) throw new Error(`API error ${res.status}`);
        const data = await res.json();

        if (!data.length) {
            grid.innerHTML = `<p class="no-results">No shadow predictions found yet. Ensure shadow_daemon.py is running.</p>`;
        } else {
            data.forEach(p => {
                const probA = Math.round(p.probability * 100);
                const probB = 100 - probA;
                
                let actualHtml = "";
                if (p.actual_winner) {
                    const isCorrect = p.actual_winner === p.predicted_winner;
                    actualHtml = `<div style="margin-top:10px; color:${isCorrect ? '#10b981' : '#ef4444'}">
                        <strong>Actual Winner:</strong> ${p.actual_winner} ${isCorrect ? '✅' : '❌'}
                    </div>`;
                } else {
                    actualHtml = `<div style="margin-top:10px; color:#9ca3af; font-style:italic">Match Pending...</div>`;
                }

                const card = document.createElement("div");
                card.className = "match-card";
                card.style = "border: 1px solid rgba(225, 29, 72, 0.3); background: rgba(225, 29, 72, 0.05);";
                card.innerHTML = `
                    <div class="match-meta" style="color: #e11d48">
                        <i class="fas fa-lock"></i> Locked & Sealed
                    </div>
                    <div class="match-teams" style="margin-top: 1rem;">
                        <div class="team ${p.team_a === p.predicted_winner ? 'predicted-winner' : ''}">
                            <div class="team-name">${p.team_a}</div>
                            <div class="team-prob">${probA}%</div>
                        </div>
                        <div class="vs-badge" style="background:#e11d48">VS</div>
                        <div class="team ${p.team_b === p.predicted_winner ? 'predicted-winner' : ''}">
                            <div class="team-name">${p.team_b}</div>
                            <div class="team-prob">${probB}%</div>
                        </div>
                    </div>
                    <div class="venue-info"><i class="fas fa-calendar"></i> ${p.date.split('T')[0]}</div>
                    ${actualHtml}
                `;
                grid.appendChild(card);
            });
        }
    } catch (err) {
        grid.innerHTML = `<p class="no-results" style="color:#e11d48">⚠️ ${err.message}</p>`;
    } finally {
        loader.classList.add("hidden");
        grid.classList.remove("hidden");
    }
}

