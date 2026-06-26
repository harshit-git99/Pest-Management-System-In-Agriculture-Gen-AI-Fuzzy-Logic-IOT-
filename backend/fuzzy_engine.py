from __future__ import annotations
from typing import Dict, List


def _membership_low(x: float, a: float, b: float) -> float:
    if x <= a: return 1.0
    if x >= b: return 0.0
    return (b - x) / (b - a)

def _membership_high(x: float, a: float, b: float) -> float:
    if x <= a: return 0.0
    if x >= b: return 1.0
    return (x - a) / (b - a)

def _membership_mid(x: float, a: float, b: float, c: float) -> float:
    if x <= a or x >= c: return 0.0
    if x == b: return 1.0
    if x < b: return (x - a) / (b - a)
    return (c - x) / (c - b)


def advisory(pest: str, severity: float, temperature: float, humidity: float, crop_type: str) -> Dict:
    """Mamdani-inspired fuzzy rule system returning risk and advice."""
    severity = max(0, min(100, float(severity)))
    temperature = float(temperature)
    humidity = max(0, min(100, float(humidity)))

    sev_low = _membership_low(severity, 20, 45)
    sev_med = _membership_mid(severity, 25, 55, 78)
    sev_high = _membership_high(severity, 60, 85)
    hum_high = _membership_high(humidity, 65, 88)
    temp_high = _membership_high(temperature, 28, 38)
    temp_mid = _membership_mid(temperature, 18, 28, 36)

    low_rule = max(min(sev_low, 1 - hum_high), 0.1)
    medium_rule = max(sev_med, min(sev_low, hum_high), min(sev_med, temp_mid))
    high_rule = max(sev_high, min(sev_med, hum_high, temp_high))

    numerator = low_rule * 25 + medium_rule * 58 + high_rule * 88
    denominator = max(low_rule + medium_rule + high_rule, 0.001)
    risk_score = round(numerator / denominator, 1)

    if risk_score >= 75:
        risk = "Severe"
        action = "Immediate targeted intervention required within 24 hours."
    elif risk_score >= 45:
        risk = "Moderate"
        action = "Treat affected patch and monitor again within 48 hours."
    else:
        risk = "Low"
        action = "Avoid blanket pesticide use; continue preventive monitoring."

    biological = {
        "Aphids": "Release ladybird beetles where available and spray neem-based solution on affected leaves.",
        "Whitefly": "Use yellow sticky traps, neem oil spray, and remove heavily infected leaves.",
        "Leaf Miner": "Remove mined leaves, use pheromone traps, and prefer neem/azadirachtin treatment.",
        "Stem Borer": "Use pheromone traps, destroy infected stems, and apply targeted recommended granules if threshold is crossed.",
        "Armyworm": "Use light traps, field sanitation, and Bacillus thuringiensis where available.",
        "Red Spider Mite": "Increase field humidity carefully, wash leaf underside, and use miticide only on hotspots.",
    }.get(pest, "Use integrated pest management and consult local agriculture officer for chemical dosage.")

    return {
        "risk": risk,
        "risk_score": risk_score,
        "action": action,
        "recommendations": [
            biological,
            "Use spot treatment instead of full-field spraying to reduce chemical load.",
            f"Record this case for {crop_type} and compare with the next inspection.",
            "Follow pesticide label, pre-harvest interval, and local agriculture department guidance before chemical use.",
        ],
        "fuzzy_inputs": {
            "severity": severity,
            "temperature": temperature,
            "humidity": humidity,
            "severity_low": round(sev_low, 2),
            "severity_medium": round(sev_med, 2),
            "severity_high": round(sev_high, 2),
            "humidity_high": round(hum_high, 2),
            "temperature_high": round(temp_high, 2),
        },
    }
