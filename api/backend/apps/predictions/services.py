"""Lógica de predição de risco (substitui implementação MVT removida)."""


def calculate_risk_score(vitals) -> int:
    score = 0

    if vitals.blood_pressure_systolic >= 180 or vitals.blood_pressure_diastolic >= 120:
        score += 40
    elif vitals.blood_pressure_systolic >= 140 or vitals.blood_pressure_diastolic >= 90:
        score += 20

    if vitals.heart_rate >= 120 or vitals.heart_rate <= 40:
        score += 20

    if vitals.temperature >= 38.5 or vitals.temperature <= 35:
        score += 15

    bmi = vitals.bmi
    if bmi and (bmi > 40 or bmi < 16):
        score += 15
    elif bmi and (bmi > 35 or bmi < 18.5):
        score += 10

    return min(score, 100)


def get_risk_level(score: int) -> str:
    if score >= 80:
        return 'critical'
    if score >= 60:
        return 'high'
    if score >= 40:
        return 'medium'
    return 'low'
