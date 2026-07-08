"""
GlobalPulse Ancient Prediction Engine
======================================
Combines 4 ancient civilisation systems to predict cricket outcomes:
  1. Vedic Jyotish     - Tithi, Nakshatra, Vara, planetary dignity
  2. Babylonian Omens  - Country planetary rulers vs planetary strength
  3. Chaldean Numerology - Player names → planetary energy totals
  4. Pancha Bhuta      - Five-element balance of squads vs venue

Uses the 'ephem' library for real planetary positions.
All predictions are stored and accuracy is tracked vs XGBoost over time.
"""

import math
import logging
from datetime import date, datetime
from typing import Dict, List, Any, Optional

try:
    import ephem
    HAS_EPHEM = True
except ImportError:
    HAS_EPHEM = False
    logging.warning("ephem not installed. Planetary calculations will use simplified math.")


# ══════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASES  (traditional sources)
# ══════════════════════════════════════════════════════════════════════════

# Planet numbers (Vedic): Sun=1, Moon=2, Mars=9, Mercury=5,
#   Jupiter=3, Venus=6, Saturn=8, Rahu=4, Ketu=7
PLANET_NAMES = {
    1: "Sun (Surya)",
    2: "Moon (Chandra)",
    3: "Jupiter (Guru)",
    4: "Rahu (North Node)",
    5: "Mercury (Budha)",
    6: "Venus (Shukra)",
    7: "Ketu (South Node)",
    8: "Saturn (Shani)",
    9: "Mars (Mangala)",
}

# Chaldean numerology map (A-Z → digit)
CHALDEAN = {
    'A':1,'B':2,'C':3,'D':4,'E':5,'F':8,'G':3,'H':5,'I':1,
    'J':1,'K':2,'L':3,'M':4,'N':5,'O':7,'P':8,'Q':1,'R':2,
    'S':3,'T':4,'U':6,'V':6,'W':6,'X':5,'Y':1,'Z':7
}

# Pythagorean numerology map
PYTHAGOREAN = {chr(65+i): (i % 9) + 1 for i in range(26)}

# 27 Nakshatras and their ruling planets (Vedic tradition)
NAKSHATRA_LORDS = [
    (1, "Ashwini", 7),       # Ketu
    (2, "Bharani", 6),       # Venus
    (3, "Krittika", 1),      # Sun
    (4, "Rohini", 2),        # Moon
    (5, "Mrigashira", 9),    # Mars
    (6, "Ardra", 4),         # Rahu
    (7, "Punarvasu", 3),     # Jupiter
    (8, "Pushya", 8),        # Saturn
    (9, "Ashlesha", 5),      # Mercury
    (10, "Magha", 7),        # Ketu
    (11, "Purva Phalguni", 6), # Venus
    (12, "Uttara Phalguni", 1), # Sun
    (13, "Hasta", 2),        # Moon
    (14, "Chitra", 9),       # Mars
    (15, "Swati", 4),        # Rahu
    (16, "Vishakha", 3),     # Jupiter
    (17, "Anuradha", 8),     # Saturn
    (18, "Jyeshtha", 5),     # Mercury
    (19, "Mula", 7),         # Ketu
    (20, "Purva Ashadha", 6), # Venus
    (21, "Uttara Ashadha", 1), # Sun
    (22, "Shravana", 2),     # Moon
    (23, "Dhanishtha", 9),   # Mars
    (24, "Shatabhisha", 4),  # Rahu
    (25, "Purva Bhadrapada", 3), # Jupiter
    (26, "Uttara Bhadrapada", 8), # Saturn
    (27, "Revati", 5),       # Mercury
]

# Vara (day of week) lords: 0=Sun(Sun),1=Mon(Moon),2=Tue(Mars),
#   3=Wed(Mercury), 4=Thu(Jupiter), 5=Fri(Venus), 6=Sat(Saturn)
VARA_LORDS = [1, 2, 9, 5, 3, 6, 8]
VARA_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Planetary friendships (Vedic): each planet → list of friend planets
PLANETARY_FRIENDS = {
    1: [2, 9, 3],    # Sun: friends Moon, Mars, Jupiter
    2: [1, 5, 8],    # Moon: friends Sun, Mercury, Saturn  
    3: [1, 2, 9],    # Jupiter: friends Sun, Moon, Mars
    4: [6, 8, 5],    # Rahu: friends Venus, Saturn, Mercury
    5: [1, 6],       # Mercury: friends Sun, Venus
    6: [5, 8, 4],    # Venus: friends Mercury, Saturn, Rahu
    7: [9, 8, 6],    # Ketu: friends Mars, Saturn, Venus
    8: [5, 6, 4],    # Saturn: friends Mercury, Venus, Rahu
    9: [1, 2, 3],    # Mars: friends Sun, Moon, Jupiter
}

# Country → ruling planet (Jyotish / Babylonian tradition)
COUNTRY_PLANETS = {
    "india":        [3, 6],     # Jupiter (dharma) + Venus (beauty/art)
    "australia":    [1, 9],     # Sun (fire) + Mars (warrior energy)
    "england":      [8, 2],     # Saturn (cold/melancholic) + Moon
    "pakistan":     [9, 4],     # Mars (warrior) + Rahu (outsider)
    "south africa": [9, 8],     # Mars + Saturn (southern hemisphere)
    "new zealand":  [2, 3],     # Moon (island) + Jupiter (peace)
    "west indies":  [1, 9],     # Sun (Caribbean sun) + Mars (power)
    "sri lanka":    [3, 2],     # Jupiter (Buddhist) + Moon (island)
    "bangladesh":   [2, 5],     # Moon (delta) + Mercury (commerce)
    "zimbabwe":     [9, 8],     # Mars + Saturn
    "afghanistan":  [9, 4],     # Mars + Rahu
    "ireland":      [2, 6],     # Moon (Celtic) + Venus
    "netherlands":  [5, 6],     # Mercury (trade) + Venus
    "scotland":     [8, 2],     # Saturn + Moon
    "namibia":      [1, 8],     # Sun + Saturn (desert)
    "oman":         [1, 9],     # Sun (Middle East) + Mars
    "uae":          [1, 6],     # Sun + Venus
    "nepal":        [3, 2],     # Jupiter (Himalayas) + Moon
    "usa":          [5, 9],     # Mercury (commerce) + Mars
    "canada":       [8, 2],     # Saturn (cold) + Moon
}

# Pancha Bhuta (five elements) → planet ruler mapping
# Fire: Sun(1), Mars(9)   Earth: Mercury(5), Saturn(8)
# Water: Moon(2), Venus(6)  Air: Rahu(4), Saturn(8)  Ether: Jupiter(3), Ketu(7)
ELEMENT_MAP = {
    1: "Fire",    # Sun
    2: "Water",   # Moon
    3: "Ether",   # Jupiter
    4: "Air",     # Rahu
    5: "Earth",   # Mercury
    6: "Water",   # Venus
    7: "Ether",   # Ketu
    8: "Earth",   # Saturn
    9: "Fire",    # Mars
}

# Venue → dominant element (based on geography)
VENUE_ELEMENTS = {
    "melbourne cricket ground":     "Air",
    "mcg":                          "Air",
    "sydney cricket ground":        "Water",
    "scg":                          "Water",
    "wankhede stadium":             "Water",   # coastal Mumbai
    "eden gardens":                 "Water",   # Kolkata delta
    "narendra modi stadium":        "Earth",   # landlocked Ahmedabad
    "lord's":                       "Air",
    "the oval":                     "Earth",
    "headingley":                   "Air",
    "wanderers stadium":            "Fire",    # high altitude Johannesburg
    "newlands":                     "Water",   # Cape Town coast
    "gaddafi stadium":              "Air",
    "national stadium karachi":     "Water",   # coastal Karachi
    "r.premadasa stadium":          "Water",   # island
    "kensington oval":              "Water",   # Caribbean coast
    "sabina park":                  "Water",
    "gabba":                        "Fire",    # Brisbane heat
    "perth stadium":                "Fire",    # desert heat
    "default":                      "Ether",   # neutral
}

# Planetary exaltation signs (where planet is strongest)
EXALTED_SIGNS = {1: 1, 2: 2, 3: 4, 4: 3, 5: 6, 6: 12, 7: 9, 8: 7, 9: 10}
# Debilitation signs (where planet is weakest)
DEBILITATED_SIGNS = {1: 7, 2: 8, 3: 10, 4: 9, 5: 12, 6: 6, 7: 3, 8: 1, 9: 4}


# ══════════════════════════════════════════════════════════════════════════
# PLANETARY CALCULATOR
# ══════════════════════════════════════════════════════════════════════════

class PlanetaryCalculator:
    """Calculates real planetary positions using ephem library."""

    def __init__(self, match_date: date):
        self.match_date = match_date
        self._positions = None

    def get_positions(self) -> Dict[str, Any]:
        """Returns planetary positions as zodiac sign (1-12) and degree."""
        if self._positions:
            return self._positions

        if not HAS_EPHEM:
            return self._simplified_positions()

        dt = datetime(self.match_date.year, self.match_date.month, self.match_date.day, 6, 0, 0)
        d = ephem.Date(dt)

        bodies = {
            1: ephem.Sun(),
            2: ephem.Moon(),
            3: ephem.Jupiter(),
            4: None,   # Rahu (North Node) — calculated separately
            5: ephem.Mercury(),
            6: ephem.Venus(),
            7: None,   # Ketu = Rahu + 180
            8: ephem.Saturn(),
            9: ephem.Mars(),
        }

        result = {}
        rahu_lon = None

        for planet_num, body in bodies.items():
            if body is None:
                continue
            body.compute(d)
            lon_deg = math.degrees(body.hlong)  # ecliptic longitude
            sign = int(lon_deg / 30) + 1        # zodiac sign 1-12
            speed = 1.0  # simplified — actual retrograde needs two computations

            # Detect retrograde by computing tomorrow's position
            body_tomorrow = body.__class__()
            body_tomorrow.compute(ephem.Date(d + 1))
            lon_tomorrow = math.degrees(body_tomorrow.hlong)
            retrograde = lon_tomorrow < lon_deg

            result[planet_num] = {
                "longitude": lon_deg,
                "sign": sign,
                "retrograde": retrograde,
                "exalted": sign == EXALTED_SIGNS.get(planet_num),
                "debilitated": sign == DEBILITATED_SIGNS.get(planet_num),
            }
            if planet_num == 2:  # Moon
                moon_lon = lon_deg
            if planet_num == 1:  # Sun
                sun_lon = lon_deg

        # Rahu (North Node)
        try:
            node = ephem.TrueNorthNode()
            node.compute(d)
            rahu_lon = math.degrees(node.hlong)
            rahu_sign = int(rahu_lon / 30) + 1
            result[4] = {"longitude": rahu_lon, "sign": rahu_sign, "retrograde": True, "exalted": False, "debilitated": False}
            result[7] = {"longitude": (rahu_lon + 180) % 360, "sign": ((rahu_sign + 5) % 12) + 1, "retrograde": True, "exalted": False, "debilitated": False}
        except Exception:
            result[4] = {"longitude": 0, "sign": 1, "retrograde": True, "exalted": False, "debilitated": False}
            result[7] = {"longitude": 180, "sign": 7, "retrograde": True, "exalted": False, "debilitated": False}

        # Tithi and Nakshatra
        try:
            tithi_angle = (moon_lon - sun_lon) % 360
            tithi = int(tithi_angle / 12) + 1
            nakshatra_num = int(moon_lon / (360 / 27)) + 1
        except Exception:
            tithi, nakshatra_num = 15, 14

        result["tithi"] = tithi
        result["nakshatra"] = nakshatra_num
        result["vara"] = self.match_date.weekday() + 1  # 1=Mon, 7=Sun
        result["vara_lord"] = VARA_LORDS[self.match_date.weekday()]
        result["nakshatra_lord"] = NAKSHATRA_LORDS[min(nakshatra_num - 1, 26)][2]
        result["nakshatra_name"] = NAKSHATRA_LORDS[min(nakshatra_num - 1, 26)][1]

        self._positions = result
        return result

    def _simplified_positions(self) -> Dict[str, Any]:
        """Fallback: rough positions based on date math (no ephem)."""
        day_of_year = self.match_date.timetuple().tm_yday
        year = self.match_date.year

        # Very rough orbital periods
        positions = {}
        for p, period_days, offset in [
            (1, 365, 0), (2, 27.3, 0), (3, 4333, 30),
            (5, 88, 0), (6, 225, 45), (8, 10759, 270), (9, 687, 90)
        ]:
            total_days = (year - 2000) * 365 + day_of_year + offset
            lon = (total_days / period_days * 360) % 360
            sign = int(lon / 30) + 1
            positions[p] = {"longitude": lon, "sign": sign, "retrograde": False,
                           "exalted": sign == EXALTED_SIGNS.get(p),
                           "debilitated": sign == DEBILITATED_SIGNS.get(p)}

        moon_lon = positions[2]["longitude"]
        sun_lon = positions[1]["longitude"]
        positions[4] = {"longitude": (sun_lon + 180) % 360, "sign": int(((sun_lon + 180) % 360) / 30) + 1,
                        "retrograde": True, "exalted": False, "debilitated": False}
        positions[7] = {"longitude": sun_lon, "sign": int(sun_lon / 30) + 1,
                        "retrograde": True, "exalted": False, "debilitated": False}

        tithi = int(((moon_lon - sun_lon) % 360) / 12) + 1
        nakshatra_num = int(moon_lon / (360 / 27)) + 1
        positions["tithi"] = tithi
        positions["nakshatra"] = nakshatra_num
        positions["vara"] = self.match_date.weekday() + 1
        positions["vara_lord"] = VARA_LORDS[self.match_date.weekday()]
        positions["nakshatra_lord"] = NAKSHATRA_LORDS[nakshatra_num - 1][2]
        positions["nakshatra_name"] = NAKSHATRA_LORDS[nakshatra_num - 1][1]
        self._positions = positions
        return positions


# ══════════════════════════════════════════════════════════════════════════
# NUMEROLOGY ENGINE
# ══════════════════════════════════════════════════════════════════════════

def chaldean_name_number(name: str) -> int:
    """Reduce a player's name to a Chaldean single digit (1-9)."""
    total = sum(CHALDEAN.get(c.upper(), 0) for c in name if c.isalpha())
    while total > 9:
        total = sum(int(d) for d in str(total))
    return max(1, total)

def pythagorean_name_number(name: str) -> int:
    """Reduce a player's name to a Pythagorean single digit (1-9)."""
    total = sum(PYTHAGOREAN.get(c.upper(), 0) for c in name if c.isalpha())
    while total > 9:
        total = sum(int(d) for d in str(total))
    return max(1, total)

def team_numerology_profile(players: List[str]) -> Dict[int, int]:
    """Returns {planet_number: count_of_players} for a squad."""
    profile = {p: 0 for p in range(1, 10)}
    for player in players:
        num = chaldean_name_number(player)
        profile[num] = profile.get(num, 0) + 1
    return profile


# ══════════════════════════════════════════════════════════════════════════
# THE 4 PREDICTION SYSTEMS
# ══════════════════════════════════════════════════════════════════════════

def _score_planet(planet_num: int, positions: Dict) -> float:
    """Returns a strength score for a planet on the given day (-2 to +2)."""
    if planet_num not in positions:
        return 0.0
    p = positions[planet_num]
    score = 0.0
    if p.get("exalted"):     score += 2.0
    if p.get("debilitated"): score -= 2.0
    if p.get("retrograde"):  score -= 0.5
    # Friendly with Vara lord?
    vara_lord = positions.get("vara_lord", 0)
    if vara_lord in PLANETARY_FRIENDS.get(planet_num, []):
        score += 0.5
    return score


def predict_jyotish(
    team_a: str, team_b: str, players_a: List[str], players_b: List[str],
    match_date: date, calc: PlanetaryCalculator
) -> Dict[str, Any]:
    """Vedic Jyotish prediction system."""
    pos = calc.get_positions()
    tithi = pos.get("tithi", 15)
    nakshatra_name = pos.get("nakshatra_name", "Unknown")
    nakshatra_lord = pos.get("nakshatra_lord", 3)
    vara_lord = pos.get("vara_lord", 1)
    vara_name = VARA_NAMES[match_date.weekday()]

    # Get country planet rulers
    def get_country_planets(team_name: str) -> List[int]:
        key = team_name.lower().split(" ")[0]
        for k, planets in COUNTRY_PLANETS.items():
            if k in team_name.lower():
                return planets
        return [3, 1]  # Default: Jupiter + Sun

    planets_a = get_country_planets(team_a)
    planets_b = get_country_planets(team_b)

    # Score each team's ruling planets
    score_a = sum(_score_planet(p, pos) for p in planets_a)
    score_b = sum(_score_planet(p, pos) for p in planets_b)

    # Nakshatra lord friendly to which team?
    for p in planets_a:
        if nakshatra_lord in PLANETARY_FRIENDS.get(p, []) or nakshatra_lord == p:
            score_a += 1.0
    for p in planets_b:
        if nakshatra_lord in PLANETARY_FRIENDS.get(p, []) or nakshatra_lord == p:
            score_b += 1.0

    # Tithi influence: odd Tithis favour action (batting side), even favour defence
    tithi_type = "Shukla (waxing)" if tithi <= 15 else "Krishna (waning)"

    # Normalize to probability
    total = abs(score_a) + abs(score_b) + 0.001
    prob_a = round(0.5 + (score_a - score_b) / (2 * (total + 2)), 4)
    prob_a = max(0.35, min(0.85, prob_a))

    explanation = (
        f"Vara: {vara_name} (lord: {PLANET_NAMES[vara_lord]}). "
        f"Nakshatra: {nakshatra_name} (lord: {PLANET_NAMES[nakshatra_lord]}). "
        f"Tithi: {tithi} — {tithi_type}. "
        f"{team_a} ruling planets score: {score_a:.1f}. "
        f"{team_b} ruling planets score: {score_b:.1f}."
    )

    return {
        "system": "Vedic Jyotish",
        "emoji": "🪐",
        "team_a_prob": prob_a,
        "team_b_prob": round(1 - prob_a, 4),
        "predicted_winner": team_a if prob_a >= 0.5 else team_b,
        "confidence": round(abs(prob_a - 0.5) * 2, 4),
        "explanation": explanation,
        "details": {
            "tithi": tithi, "nakshatra": nakshatra_name,
            "vara": vara_name, "vara_lord": PLANET_NAMES[vara_lord],
            "nakshatra_lord": PLANET_NAMES[nakshatra_lord],
        }
    }


def predict_babylonian(
    team_a: str, team_b: str,
    match_date: date, calc: PlanetaryCalculator
) -> Dict[str, Any]:
    """Babylonian planetary omen system."""
    pos = calc.get_positions()

    def get_country_planets(team_name: str) -> List[int]:
        for k, planets in COUNTRY_PLANETS.items():
            if k in team_name.lower():
                return planets
        return [3, 1]

    planets_a = get_country_planets(team_a)
    planets_b = get_country_planets(team_b)

    # Babylonian key rule: Jupiter strong = "King of the East" (India/Asia) wins
    jupiter_score = _score_planet(3, pos)
    mars_score = _score_planet(9, pos)
    venus_score = _score_planet(6, pos)
    saturn_score = _score_planet(8, pos)
    moon_score = _score_planet(2, pos)

    omens = []
    score_a, score_b = 0.0, 0.0

    for p in planets_a:
        s = _score_planet(p, pos)
        score_a += s
        state = "exalted" if pos.get(p, {}).get("exalted") else ("retrograde" if pos.get(p, {}).get("retrograde") else "normal")
        if abs(s) > 0.3:
            omens.append(f"{PLANET_NAMES[p]} is {state} → favours {team_a}" if s > 0 else f"{PLANET_NAMES[p]} is {state} → unfavours {team_a}")

    for p in planets_b:
        s = _score_planet(p, pos)
        score_b += s
        state = "exalted" if pos.get(p, {}).get("exalted") else ("retrograde" if pos.get(p, {}).get("retrograde") else "normal")
        if abs(s) > 0.3:
            omens.append(f"{PLANET_NAMES[p]} is {state} → favours {team_b}" if s > 0 else f"{PLANET_NAMES[p]} is {state} → unfavours {team_b}")

    # Special Babylonian rule: Mars retrograde = defender (lower batting order) wins
    if pos.get(9, {}).get("retrograde"):
        omens.append("Mars retrograde — defensive strategy prevails")

    prob_a = round(0.5 + (score_a - score_b) / (2 * (abs(score_a) + abs(score_b) + 2)), 4)
    prob_a = max(0.35, min(0.85, prob_a))

    return {
        "system": "Babylonian Omens",
        "emoji": "⭐",
        "team_a_prob": prob_a,
        "team_b_prob": round(1 - prob_a, 4),
        "predicted_winner": team_a if prob_a >= 0.5 else team_b,
        "confidence": round(abs(prob_a - 0.5) * 2, 4),
        "explanation": " | ".join(omens[:4]) if omens else "Planetary positions neutral.",
        "details": {
            "jupiter": "exalted" if pos.get(3, {}).get("exalted") else "normal",
            "mars": "retrograde" if pos.get(9, {}).get("retrograde") else "direct",
            "venus": "exalted" if pos.get(6, {}).get("exalted") else "normal",
            "saturn": "exalted" if pos.get(8, {}).get("exalted") else "normal",
        }
    }


def predict_numerology(
    team_a: str, team_b: str,
    players_a: List[str], players_b: List[str],
    match_date: date, calc: PlanetaryCalculator
) -> Dict[str, Any]:
    """Chaldean Numerology system based on player names."""
    pos = calc.get_positions()

    profile_a = team_numerology_profile(players_a)
    profile_b = team_numerology_profile(players_b)

    # Score each team: sum of (planet_count × planet_strength_today)
    score_a, score_b = 0.0, 0.0
    insights_a, insights_b = [], []

    for planet_num in range(1, 10):
        strength = _score_planet(planet_num, pos)
        count_a = profile_a.get(planet_num, 0)
        count_b = profile_b.get(planet_num, 0)
        score_a += count_a * strength
        score_b += count_b * strength
        if count_a > 0 and abs(strength) > 0.3:
            state = "STRONG" if strength > 0 else "WEAK"
            insights_a.append(f"{count_a}× {PLANET_NAMES[planet_num]} ({state})")
        if count_b > 0 and abs(strength) > 0.3:
            state = "STRONG" if strength > 0 else "WEAK"
            insights_b.append(f"{count_b}× {PLANET_NAMES[planet_num]} ({state})")

    # Match date numerology
    date_num = sum(int(d) for d in match_date.isoformat().replace("-", ""))
    while date_num > 9:
        date_num = sum(int(d) for d in str(date_num))
    date_planet = date_num

    prob_a = round(0.5 + (score_a - score_b) / (2 * (abs(score_a) + abs(score_b) + 2)), 4)
    prob_a = max(0.35, min(0.85, prob_a))

    explanation = (
        f"Match date number: {date_num} ({PLANET_NAMES[date_planet]}). "
        f"{team_a} squad energy: {', '.join(insights_a[:3]) or 'Neutral'}. "
        f"{team_b} squad energy: {', '.join(insights_b[:3]) or 'Neutral'}."
    )

    if not players_a and not players_b:
        explanation = "No squad data available — using team name numerology only."
        team_a_num = chaldean_name_number(team_a)
        team_b_num = chaldean_name_number(team_b)
        score_a = _score_planet(team_a_num, pos)
        score_b = _score_planet(team_b_num, pos)
        prob_a = round(0.5 + (score_a - score_b) / (abs(score_a) + abs(score_b) + 2), 4)
        prob_a = max(0.35, min(0.85, prob_a))

    return {
        "system": "Chaldean Numerology",
        "emoji": "🔢",
        "team_a_prob": prob_a,
        "team_b_prob": round(1 - prob_a, 4),
        "predicted_winner": team_a if prob_a >= 0.5 else team_b,
        "confidence": round(abs(prob_a - 0.5) * 2, 4),
        "explanation": explanation,
        "details": {
            "date_number": date_num,
            "date_planet": PLANET_NAMES[date_planet],
            "team_a_dominant": PLANET_NAMES[max(profile_a, key=profile_a.get)] if players_a else "N/A",
            "team_b_dominant": PLANET_NAMES[max(profile_b, key=profile_b.get)] if players_b else "N/A",
        }
    }


def predict_pancha_bhuta(
    team_a: str, team_b: str,
    players_a: List[str], players_b: List[str],
    venue: str
) -> Dict[str, Any]:
    """Pancha Bhuta (Five Elements) system."""
    # Venue element
    venue_key = venue.lower()
    venue_element = VENUE_ELEMENTS.get("default", "Ether")
    for key, element in VENUE_ELEMENTS.items():
        if key in venue_key:
            venue_element = element
            break

    def squad_elements(players: List[str]) -> Dict[str, float]:
        elem_count = {e: 0 for e in ["Fire", "Earth", "Water", "Air", "Ether"]}
        if not players:
            # Fall back to team name
            return elem_count
        for p in players:
            num = chaldean_name_number(p)
            elem = ELEMENT_MAP.get(num, "Ether")
            elem_count[elem] += 1
        return elem_count

    elements_a = squad_elements(players_a)
    elements_b = squad_elements(players_b)

    # Score: team whose dominant element matches or is friendly to venue element
    ELEMENT_FRIENDS = {
        "Fire":  ["Fire", "Air"],
        "Earth": ["Earth", "Water"],
        "Water": ["Water", "Earth"],
        "Air":   ["Air", "Fire"],
        "Ether": ["Ether", "Fire", "Air"],
    }
    friendly = ELEMENT_FRIENDS.get(venue_element, [])

    score_a = sum(elements_a.get(e, 0) for e in friendly)
    score_b = sum(elements_b.get(e, 0) for e in friendly)

    total = score_a + score_b + 0.001
    prob_a = round(0.5 + (score_a - score_b) / (2 * (total + 2)), 4)
    prob_a = max(0.35, min(0.85, prob_a))

    dom_a = max(elements_a, key=elements_a.get) if players_a else "N/A"
    dom_b = max(elements_b, key=elements_b.get) if players_b else "N/A"

    if not players_a and not players_b:
        # Team-name element
        num_a = chaldean_name_number(team_a)
        num_b = chaldean_name_number(team_b)
        dom_a = ELEMENT_MAP.get(num_a, "Ether")
        dom_b = ELEMENT_MAP.get(num_b, "Ether")
        score_a = 1 if dom_a in friendly else 0
        score_b = 1 if dom_b in friendly else 0
        prob_a = round(0.5 + (score_a - score_b) / 4, 4)
        prob_a = max(0.35, min(0.85, prob_a))

    explanation = (
        f"Venue '{venue}' carries {venue_element} energy. "
        f"{team_a}'s dominant element: {dom_a} ({'✓ Harmonious' if dom_a in friendly else '✗ Discordant'}). "
        f"{team_b}'s dominant element: {dom_b} ({'✓ Harmonious' if dom_b in friendly else '✗ Discordant'})."
    )

    return {
        "system": "Pancha Bhuta",
        "emoji": "🌿",
        "team_a_prob": prob_a,
        "team_b_prob": round(1 - prob_a, 4),
        "predicted_winner": team_a if prob_a >= 0.5 else team_b,
        "confidence": round(abs(prob_a - 0.5) * 2, 4),
        "explanation": explanation,
        "details": {
            "venue_element": venue_element,
            "team_a_element": dom_a,
            "team_b_element": dom_b,
            "friendly_elements": friendly,
        }
    }


# ══════════════════════════════════════════════════════════════════════════
# MASTER ANCIENT ENGINE
# ══════════════════════════════════════════════════════════════════════════

class AncientPredictionEngine:
    """
    Runs all 4 ancient systems and returns a consensus prediction.
    Results are stored in DB for long-term accuracy tracking.
    """

    def predict(
        self,
        team_a: str,
        team_b: str,
        match_date: date,
        venue: str,
        players_a: Optional[List[str]] = None,
        players_b: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        players_a = players_a or []
        players_b = players_b or []
        calc = PlanetaryCalculator(match_date)

        systems = [
            predict_jyotish(team_a, team_b, players_a, players_b, match_date, calc),
            predict_babylonian(team_a, team_b, match_date, calc),
            predict_numerology(team_a, team_b, players_a, players_b, match_date, calc),
            predict_pancha_bhuta(team_a, team_b, players_a, players_b, venue),
        ]

        # Weighted consensus: Jyotish 40%, Babylonian 25%, Numerology 20%, Bhuta 15%
        weights = [0.40, 0.25, 0.20, 0.15]
        consensus_prob_a = sum(s["team_a_prob"] * w for s, w in zip(systems, weights))
        consensus_winner = team_a if consensus_prob_a >= 0.5 else team_b
        consensus_confidence = abs(consensus_prob_a - 0.5) * 2

        # Planetary snapshot for display
        pos = calc.get_positions()
        planetary_snapshot = {
            PLANET_NAMES[p]: {
                "sign": pos[p]["sign"],
                "exalted": pos[p]["exalted"],
                "retrograde": pos[p]["retrograde"],
            }
            for p in [1, 2, 3, 5, 6, 8, 9] if p in pos
        }

        return {
            "team_a": team_a,
            "team_b": team_b,
            "match_date": match_date.isoformat(),
            "venue": venue,
            "players_a_count": len(players_a),
            "players_b_count": len(players_b),
            "systems": systems,
            "consensus": {
                "predicted_winner": consensus_winner,
                "team_a_prob": round(consensus_prob_a, 4),
                "team_b_prob": round(1 - consensus_prob_a, 4),
                "confidence": round(consensus_confidence, 4),
            },
            "planetary_snapshot": planetary_snapshot,
            "panchanga": {
                "tithi": pos.get("tithi"),
                "nakshatra": pos.get("nakshatra_name"),
                "vara": VARA_NAMES[match_date.weekday()],
                "vara_lord": PLANET_NAMES.get(pos.get("vara_lord", 3)),
            }
        }
