"""Trains the real classifier and exports model.pkl + encoders.pkl into
backend/, in the exact structure backend/model.py's _real_predict() expects
(documented in backend/README.md).

The dataset is fully labeled with 6 mutually exclusive classes (normal +
5 named attack types), so this trains a supervised multi-class
RandomForestClassifier rather than an unsupervised anomaly detector
(e.g. Isolation Forest): Isolation Forest only scores "how anomalous" a row
is, it can't name which attack it is, and PredictionResponse.label needs
the specific attack name (ddos, port_scan, ...), not just "anomaly".
"""

import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "traffic_emergency_cyber_dataset.csv"
BACKEND_DIR = ROOT_DIR / "backend"

CATEGORICAL_COLS = ["device_type", "zone_id", "protocol", "mqtt_msg_type", "day_type"]
NUMERIC_COLS = [
    "src_port", "dst_port", "packet_size", "packets_per_second",
    "connection_duration", "bytes_transferred", "unique_dst_ips_contacted",
    "avg_request_interval", "syn_flag_count", "rst_flag_count",
    "failed_login_attempts", "is_encrypted", "mac_ip_mismatch",
    "signal_preemption_request", "gps_deviation_km", "hour_of_day",
]
# Matches TrafficRow's field order in backend/schemas.py exactly.
FEATURE_ORDER = [
    "device_type", "zone_id", "protocol", "mqtt_msg_type",
    "src_port", "dst_port", "packet_size", "packets_per_second",
    "connection_duration", "bytes_transferred", "unique_dst_ips_contacted",
    "avg_request_interval", "syn_flag_count", "rst_flag_count",
    "failed_login_attempts", "is_encrypted", "mac_ip_mismatch",
    "signal_preemption_request", "gps_deviation_km", "hour_of_day",
    "day_type",
]


def main():
    df = pd.read_csv(DATA_PATH)

    encoders = {}
    for col in CATEGORICAL_COLS:
        encoder = LabelEncoder()
        df[col] = encoder.fit_transform(df[col].astype(str))
        encoders[col] = encoder

    scaler = StandardScaler()
    df[NUMERIC_COLS] = scaler.fit_transform(df[NUMERIC_COLS])

    X = df[FEATURE_ORDER]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    clf = RandomForestClassifier(
        n_estimators=300, max_depth=None, class_weight="balanced", random_state=42
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print(f"Test accuracy: {accuracy_score(y_test, y_pred):.4f}\n")
    print(classification_report(y_test, y_pred))
    print("Confusion matrix (rows=actual, cols=predicted), labels:", list(clf.classes_))
    print(confusion_matrix(y_test, y_pred, labels=clf.classes_))

    model_path = BACKEND_DIR / "model.pkl"
    encoders_path = BACKEND_DIR / "encoders.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(clf, f)

    artifacts = {
        "encoders": encoders,
        "scaler": scaler,
        "numeric_cols": NUMERIC_COLS,
        "feature_order": FEATURE_ORDER,
    }
    with open(encoders_path, "wb") as f:
        pickle.dump(artifacts, f)

    print(f"\nSaved {model_path}")
    print(f"Saved {encoders_path}")


if __name__ == "__main__":
    main()
