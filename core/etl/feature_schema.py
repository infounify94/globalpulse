# Canonical feature schema and strict ordering for GlobalPulse V1.0
# Guaranteed 100% identical feature ordering between run_train.py and run_predict.py

CANONICAL_FEATURE_ORDER = [
    "stat_team_a_win_pct_5",
    "stat_team_a_win_pct_10",
    "stat_team_a_win_pct_all",
    "stat_team_b_win_pct_5",
    "stat_team_b_win_pct_10",
    "stat_team_b_win_pct_all",
    "stat_h2h_team_a_win_pct",
    "stat_venue_team_a_win_pct",
    "stat_venue_team_b_win_pct",
    "stat_team_a_elo",
    "stat_team_b_elo",
    "anc_consensus_prob_a",
    "anc_jyotish_prob_a",
    "anc_babylonian_prob_a",
    "anc_numerology_prob_a",
    "anc_astronomy_prob_a",
    "anc_pattern_prob_a",
]

FEATURE_HUMAN_NAMES = {
    "stat_team_a_win_pct_5": "Last 5 Form (Team A)",
    "stat_team_a_win_pct_10": "Last 10 Form (Team A)",
    "stat_team_a_win_pct_all": "All-Time Form (Team A)",
    "stat_team_b_win_pct_5": "Last 5 Form (Team B)",
    "stat_team_b_win_pct_10": "Last 10 Form (Team B)",
    "stat_team_b_win_pct_all": "All-Time Form (Team B)",
    "stat_h2h_team_a_win_pct": "Head-to-Head Win %",
    "stat_venue_team_a_win_pct": "Venue Record (Team A)",
    "stat_venue_team_b_win_pct": "Venue Record (Team B)",
    "stat_team_a_elo": "Elo Rating (Team A)",
    "stat_team_b_elo": "Elo Rating (Team B)",
    "anc_consensus_prob_a": "Ancient Consensus Signal",
    "anc_jyotish_prob_a": "Vedic Jyotish Alignment",
    "anc_babylonian_prob_a": "Babylonian Planetary Signal",
    "anc_numerology_prob_a": "Vedic Numerology Resonance",
    "anc_astronomy_prob_a": "Astronomical Solar/Lunar Phase",
    "anc_pattern_prob_a": "Pattern Memory Matrix",
}
