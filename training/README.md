# Model training

Trains the real classifier that `backend/model.py` loads, and exports it in
the exact shape `backend/README.md` documents.

## Why RandomForest, not Isolation Forest

The dataset is fully labeled with 6 mutually exclusive classes (`normal`
plus 5 named attack types). Isolation Forest is unsupervised — it can only
score "how anomalous is this row," it can't say *which* attack it is. Since
`PredictionResponse.label` needs the specific attack name (`ddos`,
`port_scan`, ...), this trains a supervised multi-class
`RandomForestClassifier` on the labeled data instead.

## Setup

```bash
pip install scikit-learn pandas
```

## Run

```bash
cd training
python train_model.py
```

This reads `../traffic_emergency_cyber_dataset.csv`, does an 80/20
stratified train/test split, fits label encoders + a scaler + the
classifier, prints a held-out classification report, and writes
`../backend/model.pkl` and `../backend/encoders.pkl`.

Restart the backend afterward — it auto-detects both files at import time.

## Current model performance

99.94% accuracy on the held-out 20% (1800 rows), with only a single
misclassification (one `command_injection` row predicted as `normal`) across
all 6 classes. This is expected to be near-perfect: the dataset's attack
classes have clean, well-separated feature signatures by construction (see
`backend/model.py`'s docstring for the same thresholds derived for the
heuristic fallback). A real-world deployment would need out-of-distribution
and adversarial-robustness testing before trusting numbers this clean.
