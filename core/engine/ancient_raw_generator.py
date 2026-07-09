import math
from datetime import date
from typing import Dict, Any, List

from core.engine.ancient_engine import (
    PlanetaryCalculator, chaldean_name_number, 
    ELEMENT_MAP, VENUE_ELEMENTS, COUNTRY_PLANETS,
    PLANET_NAMES
)

def _get_country_planets(team_name: str) -> List[int]:
    key = team_name.lower().split(" ")[0]
    for k, planets in COUNTRY_PLANETS.items():
        if k in team_name.lower():
            return planets
    return [3, 1]  # Default: Jupiter + Sun

def get_vedic_features(match_date: date, team_a: str, team_b: str, calc: PlanetaryCalculator) -> Dict[str, Any]:
    pos = calc.get_positions()
    
    # 1=Sun, 2=Moon, 3=Jupiter, 4=Rahu, 5=Mercury, 6=Venus, 7=Ketu, 8=Saturn, 9=Mars
    features = {
        "tithi": pos.get("tithi", 15),
        "nakshatra_num": pos.get("nakshatra", 14),
        "vara_num": pos.get("vara", 1),
        "sun_sign": pos.get(1, {}).get("sign", 1),
        "moon_sign": pos.get(2, {}).get("sign", 1),
    }

    # Planet strengths (0 to 3 scale roughly: 1 normal, 2 exalted, 0 debilitated)
    # Plus retrograde boolean (1/0)
    for p_num in range(1, 10):
        p_data = pos.get(p_num, {})
        strength = 1
        if p_data.get("exalted"):
            strength = 2
        elif p_data.get("debilitated"):
            strength = 0
            
        features[f"planet_{p_num}_strength"] = strength
        features[f"planet_{p_num}_retrograde"] = 1 if p_data.get("retrograde") else 0

    # Team specific vedic rulers
    planets_a = _get_country_planets(team_a)
    planets_b = _get_country_planets(team_b)
    
    features["team_a_primary_ruler"] = planets_a[0]
    features["team_b_primary_ruler"] = planets_b[0]
    
    return features

def get_babylonian_features(match_date: date, team_a: str, team_b: str, calc: PlanetaryCalculator) -> Dict[str, Any]:
    pos = calc.get_positions()
    
    # Babylonian system focuses heavily on visible planets and omens
    # Jupiter=3, Mars=9, Saturn=8, Venus=6, Mercury=5, Moon=2
    features = {}
    for p_num, name in [(3, "jupiter"), (9, "mars"), (8, "saturn"), (6, "venus"), (5, "mercury"), (2, "moon")]:
        p_data = pos.get(p_num, {})
        features[f"{name}_position"] = p_data.get("longitude", 0.0)
        features[f"{name}_sign"] = p_data.get("sign", 1)
        features[f"{name}_retrograde"] = 1 if p_data.get("retrograde") else 0

    # Moon phase approximation (0 to 1)
    sun_lon = pos.get(1, {}).get("longitude", 0.0)
    moon_lon = pos.get(2, {}).get("longitude", 0.0)
    moon_phase = ((moon_lon - sun_lon) % 360) / 360.0
    features["moon_phase"] = moon_phase

    return features

def get_numerology_features(match_date: date, team_a: str, team_b: str) -> Dict[str, Any]:
    team_a_num = chaldean_name_number(team_a)
    team_b_num = chaldean_name_number(team_b)
    
    # Match date numerology
    date_num = sum(int(d) for d in match_date.isoformat().replace("-", ""))
    while date_num > 9:
        date_num = sum(int(d) for d in str(date_num))
        
    return {
        "team_a_number": team_a_num,
        "team_b_number": team_b_num,
        "match_day_number": date_num,
        "team_a_match_compat": 1 if team_a_num == date_num else 0,
        "team_b_match_compat": 1 if team_b_num == date_num else 0,
    }

def get_pancha_bhuta_features(venue: str, team_a: str, team_b: str) -> Dict[str, Any]:
    venue_key = venue.lower()
    venue_element = VENUE_ELEMENTS.get("default", "Ether")
    for key, element in VENUE_ELEMENTS.items():
        if key in venue_key:
            venue_element = element
            break

    # Elements: Fire=1, Earth=2, Water=3, Air=4, Ether=5
    elem_to_int = {"Fire": 1, "Earth": 2, "Water": 3, "Air": 4, "Ether": 5}
    
    team_a_num = chaldean_name_number(team_a)
    team_b_num = chaldean_name_number(team_b)
    
    team_a_elem = ELEMENT_MAP.get(team_a_num, "Ether")
    team_b_elem = ELEMENT_MAP.get(team_b_num, "Ether")
    
    return {
        "venue_element": elem_to_int.get(venue_element, 5),
        "team_a_element": elem_to_int.get(team_a_elem, 5),
        "team_b_element": elem_to_int.get(team_b_elem, 5),
        "team_a_venue_match": 1 if team_a_elem == venue_element else 0,
        "team_b_venue_match": 1 if team_b_elem == venue_element else 0,
    }

def generate_all_ancient_raw(match_date: date, venue: str, team_a: str, team_b: str) -> Dict[str, Dict[str, Any]]:
    calc = PlanetaryCalculator(match_date)
    return {
        "vedic": get_vedic_features(match_date, team_a, team_b, calc),
        "babylonian": get_babylonian_features(match_date, team_a, team_b, calc),
        "numerology": get_numerology_features(match_date, team_a, team_b),
        "pancha_bhuta": get_pancha_bhuta_features(venue, team_a, team_b)
    }
