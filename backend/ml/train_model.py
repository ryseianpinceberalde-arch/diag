"""
Optional future training entry point.

The production system intentionally uses explainable scoring until labeled
historical failure data exists. This script shows where a supervised
Scikit-learn pipeline can be added without changing API behavior.
"""

from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib


FEATURES = [
    "cpu_usage",
    "cpu_temperature",
    "fan_speed_rpm",
    "fan_speed_percent",
    "ram_usage",
    "disk_usage",
    "disk_temperature",
    "battery_health",
    "network_latency",
    "packet_loss",
]


def train(csv_path: str, model_path: str = "ml/model.joblib") -> None:
    data = pd.read_csv(csv_path)
    missing = [column for column in FEATURES + ["failure_label"] if column not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    x_train, x_test, y_train, y_test = train_test_split(
        data[FEATURES].fillna(0),
        data["failure_label"],
        test_size=0.2,
        random_state=42,
        stratify=data["failure_label"],
    )
    pipeline = Pipeline([
        ("scale", StandardScaler()),
        ("model", RandomForestClassifier(n_estimators=200, random_state=42)),
    ])
    pipeline.fit(x_train, y_train)
    print(f"Validation accuracy: {pipeline.score(x_test, y_test):.3f}")
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)


if __name__ == "__main__":
    raise SystemExit("Call train(csv_path) after labeled failure data is available.")
