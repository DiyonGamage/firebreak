from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from firebreak.config import ROOT
from firebreak.data.psi import material_class

TARGET_THRESHOLD = 0.5
NUMERIC_FEATURES = ["o2_initial_pct", "thickness_mm", "width_mm"]
CATEGORICAL_FEATURES = ["material_class"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
ARTIFACT_PATH = ROOT / "artifacts" / "ml_severity_metrics.json"

_CACHE: dict[str, dict[str, Any]] = {}


def load_training_data(connection: sqlite3.Connection) -> pd.DataFrame:
    frame = pd.read_sql_query(
        """
        SELECT experiment_id, material, material_class, o2_initial_pct,
               thickness_mm, width_mm, delta_co2_pct
        FROM experiments
        WHERE dataset = 'BASS-II' AND delta_co2_pct IS NOT NULL
        """,
        connection,
    )
    frame["target"] = (frame["delta_co2_pct"] > TARGET_THRESHOLD).astype(int)
    return frame


def _pipeline() -> Pipeline:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = OneHotEncoder(handle_unknown="ignore")
    preprocess = ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    classifier = RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocess), ("classifier", classifier)])


def _o2_only_pipeline() -> Pipeline:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    preprocess = ColumnTransformer([("numeric", numeric, ["o2_initial_pct"])])
    classifier = RandomForestClassifier(
        n_estimators=200,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocess), ("classifier", classifier)])


def _metrics(frame: pd.DataFrame) -> dict[str, Any]:
    features = frame[FEATURES]
    target = frame["target"]
    groups = frame["material"]
    folds = GroupKFold(n_splits=5)
    probabilities = cross_val_predict(
        _pipeline(), features, target, groups=groups, cv=folds, method="predict_proba"
    )[:, 1]
    o2_probabilities = cross_val_predict(
        _o2_only_pipeline(),
        frame[["o2_initial_pct"]],
        target,
        groups=groups,
        cv=folds,
        method="predict_proba",
    )[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "n": int(len(frame)),
        "positives": int(target.sum()),
        "negatives": int(len(frame) - target.sum()),
        "positive_rate": round(float(target.mean()), 3),
        "target_threshold_delta_co2_pct": TARGET_THRESHOLD,
        "auc": round(float(roc_auc_score(target, probabilities)), 3),
        "o2_only_auc": round(float(roc_auc_score(target, o2_probabilities)), 3),
        "accuracy": round(float(accuracy_score(target, predictions)), 3),
        "balanced_accuracy": round(float(balanced_accuracy_score(target, predictions)), 3),
        "f1": round(float(f1_score(target, predictions)), 3),
        "majority_baseline_accuracy": round(
            max(float(target.mean()), 1.0 - float(target.mean())), 3
        ),
        "split": "GroupKFold(5) grouped by material description",
        "scope": "BASS-II PMMA/SIBAL/Nomex/Other; predicts CO2-rise severity, not flammability.",
    }


def _cache_key(connection: sqlite3.Connection) -> str:
    database = connection.execute("PRAGMA database_list").fetchone()
    count = connection.execute(
        "SELECT count(*) FROM experiments WHERE dataset='BASS-II' AND delta_co2_pct IS NOT NULL"
    ).fetchone()[0]
    return f"{database[2] if database else 'memory'}:{count}"


def train_and_evaluate(
    connection: sqlite3.Connection,
    save_artifact: bool = False,
) -> dict[str, Any]:
    frame = load_training_data(connection)
    metrics = _metrics(frame)
    metrics["gate"] = {
        "auc_min": 0.75,
        "auc_beats_o2_only": True,
        "passed": metrics["auc"] >= 0.75 and metrics["auc"] > metrics["o2_only_auc"],
    }
    model = _pipeline().fit(frame[FEATURES], frame["target"])
    payload = {
        "model": model,
        "frame": frame,
        "metrics": metrics,
        "classes": sorted(frame["material_class"].unique().tolist()),
    }
    _CACHE[_cache_key(connection)] = payload
    if save_artifact:
        ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return payload


def get_model(connection: sqlite3.Connection) -> dict[str, Any]:
    key = _cache_key(connection)
    if key not in _CACHE:
        train_and_evaluate(connection)
    return _CACHE[key]


def predict_severity(
    connection: sqlite3.Connection,
    material: str,
    o2_pct: float,
    thickness_mm: float | None = None,
    width_mm: float | None = None,
) -> dict[str, Any]:
    payload = get_model(connection)
    metrics = payload["metrics"]
    query_class = material_class(material)
    if query_class not in payload["classes"]:
        return {
            "enabled": False,
            "reason": f"Unseen material class '{query_class}' for the BASS-II severity model.",
            "material_class": query_class,
            "metrics": metrics,
        }
    row = pd.DataFrame(
        [
            {
                "o2_initial_pct": o2_pct,
                "thickness_mm": thickness_mm,
                "width_mm": width_mm,
                "material_class": query_class,
            }
        ]
    )
    probability = float(payload["model"].predict_proba(row)[0, 1])
    band = "high" if probability >= 0.5 else "low"
    return {
        "enabled": bool(metrics["gate"]["passed"]),
        "material_class": query_class,
        "probability_delta_co2_gt_0.5": round(probability, 3),
        "band": band,
        "metrics": metrics,
        "caveat": (
            "Within-BASS-II CO2-rise screen; not a flammability, ignition, or flight-approval prediction."
        ),
    }
