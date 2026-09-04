"""Dual-mode risk inference: trained model if available, rule-based heuristic
otherwise. main.py only ever calls predict_risk() and never needs to know
which mode is active.

Heuristic thresholds were derived by inspecting the per-label distributions
in traffic_emergency_cyber_dataset.csv (9000 rows: 6930 normal, 414 each of
ddos/port_scan/brute_force/spoofing/command_injection) rather than guessed:

- ddos:          syn_flag_count and packets_per_second jump by >10x over the
                 normal max (normal packets_per_second tops out at ~25;
                 ddos rows start at ~123). Either signal alone is decisive.
- port_scan:     unique_dst_ips_contacted starts at 12 for port_scan vs a
                 normal max of 6 - a horizontal scan touches many hosts.
- brute_force:   failed_login_attempts starts at 12 for brute_force vs a
                 normal max of 2.
- spoofing:      mac_ip_mismatch is 1 for 100% of spoofing rows and 0 for
                 every other label, so it alone is a clean separator; it's
                 paired with gps_deviation_km (spoofing min 1.55km vs normal
                 max 0.28km) per the spec.
- command_injection: signal_preemption_request is 1 on ~13% of NORMAL rows
                 too (real ambulances legitimately request green lights), so
                 it can never be used alone. Every command_injection row
                 occurs off-hours (hour < 6 or >= 21), but so do ~34% of
                 normal preemption requests, so off-hours alone is too noisy.
                 Requiring (failed_login_attempts >= 3) OR (off-hours AND
                 unencrypted) recovers 84% of command_injection rows while
                 misclassifying only ~3% of legitimate preemption requests.
"""

import pickle
from pathlib import Path

from schemas import PredictionResponse, TrafficRow

TRAINED_DEVICE_TYPES = {
    "traffic_camera",
    "signal_controller",
    "ambulance_tracker",
    "dispatch_server",
}

_BACKEND_DIR = Path(__file__).resolve().parent
_MODEL = None
_ARTIFACTS = None


def _load_trained_artifacts():
    global _MODEL, _ARTIFACTS
    model_path = _BACKEND_DIR / "model.pkl"
    encoders_path = _BACKEND_DIR / "encoders.pkl"

    if not (model_path.exists() and encoders_path.exists()):
        print("[model] model.pkl / encoders.pkl not found -> inference mode: HEURISTIC")
        return

    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        with open(encoders_path, "rb") as f:
            artifacts = pickle.load(f)
        required_keys = {"encoders", "scaler", "numeric_cols", "feature_order"}
        missing = required_keys - artifacts.keys()
        if missing:
            raise ValueError(f"encoders.pkl missing keys: {missing}")
        _MODEL = model
        _ARTIFACTS = artifacts
        print("[model] model.pkl + encoders.pkl loaded -> inference mode: TRAINED")
    except Exception as exc:
        print(f"[model] failed to load trained artifacts ({exc}); falling back to HEURISTIC mode")
        _MODEL = None
        _ARTIFACTS = None


_load_trained_artifacts()


def _risk_level(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _off_hours(hour: int) -> bool:
    return hour < 6 or hour >= 21


def _heuristic_predict(row: TrafficRow) -> PredictionResponse:
    label = "normal"
    score = 0.08 if row.signal_preemption_request else 0.05

    if row.packets_per_second > 100 or row.syn_flag_count > 100:
        label = "ddos"
        pps_component = min(row.packets_per_second / 600, 1.0)
        syn_component = min(row.syn_flag_count / 1200, 1.0)
        score = 0.75 + 0.24 * max(pps_component, syn_component)

    elif row.unique_dst_ips_contacted >= 10:
        label = "port_scan"
        score = 0.65 + 0.3 * min((row.unique_dst_ips_contacted - 10) / 100, 1.0)

    elif row.failed_login_attempts >= 10:
        label = "brute_force"
        score = 0.6 + 0.35 * min((row.failed_login_attempts - 10) / 50, 1.0)

    elif row.mac_ip_mismatch == 1 and row.gps_deviation_km > 1.0:
        label = "spoofing"
        score = 0.6 + 0.35 * min((row.gps_deviation_km - 1.0) / 13.0, 1.0)

    elif row.signal_preemption_request == 1 and (
        row.failed_login_attempts >= 3
        or (_off_hours(row.hour_of_day) and not row.is_encrypted)
    ):
        label = "command_injection"
        strength = 0.0
        if row.failed_login_attempts >= 3:
            strength += 0.5
        if _off_hours(row.hour_of_day):
            strength += 0.25
        if not row.is_encrypted:
            strength += 0.25
        score = 0.55 + 0.35 * min(strength, 1.0)

    score = round(min(max(score, 0.0), 0.99), 4)

    return PredictionResponse(
        label=label,
        risk_score=score,
        risk_level=_risk_level(score),
        device_type=row.device_type,
        zone_id=row.zone_id,
        inference_mode="heuristic",
        confidence=None,
    )


def _real_predict(row: TrafficRow) -> PredictionResponse:
    data = row.model_dump()
    encoders = _ARTIFACTS["encoders"]
    scaler = _ARTIFACTS["scaler"]
    numeric_cols = _ARTIFACTS["numeric_cols"]
    feature_order = _ARTIFACTS["feature_order"]

    encoded = dict(data)
    for col, encoder in encoders.items():
        encoded[col] = int(encoder.transform([str(data[col])])[0])

    scaled_values = scaler.transform([[data[col] for col in numeric_cols]])[0]
    for col, value in zip(numeric_cols, scaled_values):
        encoded[col] = value

    feature_vector = [[encoded[col] for col in feature_order]]

    predicted_label = str(_MODEL.predict(feature_vector)[0])
    classes = list(_MODEL.classes_)
    probas = _MODEL.predict_proba(feature_vector)[0]
    confidence = float(max(probas))

    if "normal" in classes:
        risk_score = 1.0 - float(probas[classes.index("normal")])
    else:
        risk_score = confidence

    risk_score = round(min(max(risk_score, 0.0), 1.0), 4)

    return PredictionResponse(
        label=predicted_label,
        risk_score=risk_score,
        risk_level=_risk_level(risk_score),
        device_type=row.device_type,
        zone_id=row.zone_id,
        inference_mode="trained",
        confidence=round(confidence, 4),
    )


def predict_risk(row: TrafficRow) -> PredictionResponse:
    if _MODEL is not None and row.device_type in TRAINED_DEVICE_TYPES:
        try:
            return _real_predict(row)
        except Exception as exc:
            print(f"[model] trained inference failed ({exc}); falling back to heuristic for this row")
    return _heuristic_predict(row)
