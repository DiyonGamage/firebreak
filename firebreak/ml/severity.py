from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold

from firebreak.config import ROOT
from firebreak.data.psi import material_class

TARGET_THRESHOLD = 0.5
MIN_CLASS_SUPPORT = 10
CONFORMAL_ALPHA = 0.2
N_SPLITS = 5
N_INNER_SPLITS = 3
FEATURES = ("o2_initial_pct", "thickness_mm", "material_class")
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


def _design_matrix(
    frame: pd.DataFrame,
    classes: list[str],
    medians: dict[str, float],
) -> pd.DataFrame:
    matrix = pd.DataFrame(
        {
            "o2_initial_pct": pd.to_numeric(frame["o2_initial_pct"], errors="coerce"),
            "thickness_mm": pd.to_numeric(frame["thickness_mm"], errors="coerce"),
        }
    )
    matrix["o2_initial_pct"] = matrix["o2_initial_pct"].fillna(medians["o2_initial_pct"])
    matrix["thickness_mm"] = matrix["thickness_mm"].fillna(medians["thickness_mm"])
    material_values = frame["material_class"].to_numpy()
    for name in classes:
        matrix[f"class_{name}"] = (material_values == name).astype(float)
    return matrix[["o2_initial_pct", "thickness_mm"] + [f"class_{name}" for name in classes]]


def _classifier(n_features: int, *, monotonic: bool = True) -> HistGradientBoostingClassifier:
    params: dict[str, Any] = {
        "max_iter": 200,
        "max_depth": 2,
        "learning_rate": 0.05,
        "random_state": 42,
    }
    if monotonic:
        params["monotonic_cst"] = [1] + [0] * (n_features - 1)
    return HistGradientBoostingClassifier(**params)


def _fit_folds(
    features: pd.DataFrame,
    target: np.ndarray,
    groups: np.ndarray,
) -> tuple[
    list[HistGradientBoostingClassifier],
    np.ndarray,
    np.ndarray,
    list[tuple[np.ndarray, np.ndarray]],
]:
    splits = list(GroupKFold(n_splits=N_SPLITS).split(features, target, groups))
    models: list[HistGradientBoostingClassifier] = []
    oof = np.zeros(len(features))
    fold_of = np.zeros(len(features), dtype=int)
    for fold, (train, test) in enumerate(splits):
        model = _classifier(features.shape[1]).fit(features.iloc[train], target[train])
        models.append(model)
        oof[test] = model.predict_proba(features.iloc[test])[:, 1]
        fold_of[test] = fold
    return models, oof, fold_of, splits


def _reliability(y: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    bins = []
    weighted_error = 0.0
    for lower, upper in zip(edges[:-1], edges[1:]):
        if upper == 1.0:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)
        count = int(mask.sum())
        if count == 0:
            bins.append(
                {
                    "range": [lower, upper],
                    "n": 0,
                    "mean_predicted": None,
                    "observed": None,
                }
            )
            continue
        mean_predicted = float(probabilities[mask].mean())
        observed = float(y[mask].mean())
        bins.append(
            {
                "range": [lower, upper],
                "n": count,
                "mean_predicted": round(mean_predicted, 3),
                "observed": round(observed, 3),
            }
        )
        weighted_error += (count / len(y)) * abs(mean_predicted - observed)
    return {"ece": round(weighted_error, 3), "bins": bins}


def _o2_only_auc(
    frame: pd.DataFrame,
    target: np.ndarray,
    splits: list[tuple[np.ndarray, np.ndarray]],
) -> float:
    features = (
        pd.to_numeric(frame["o2_initial_pct"], errors="coerce")
        .fillna(pd.to_numeric(frame["o2_initial_pct"], errors="coerce").median())
        .to_numpy()
        .reshape(-1, 1)
    )
    probabilities = np.zeros(len(frame))
    for train, test in splits:
        model = RandomForestClassifier(
            n_estimators=200,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(features[train], target[train])
        probabilities[test] = model.predict_proba(features[test])[:, 1]
    return float(roc_auc_score(target, probabilities))


def _monotonicity_violations(
    model: HistGradientBoostingClassifier,
    classes: list[str],
    medians: dict[str, float],
    o2_min: float,
    o2_max: float,
) -> int:
    grid = np.linspace(o2_min, o2_max, 60)
    violations = 0
    for name in classes:
        query = pd.DataFrame(
            [
                {
                    "o2_initial_pct": value,
                    "thickness_mm": medians["thickness_mm"],
                    "material_class": name,
                }
                for value in grid
            ]
        )
        matrix = _design_matrix(
            query,
            classes,
            medians,
        )
        probabilities = model.predict_proba(matrix)[:, 1]
        violations += int(np.sum(np.diff(probabilities) < -1e-9))
    return violations


def _conformal_evaluation(
    features: pd.DataFrame,
    target: np.ndarray,
    groups: np.ndarray,
    material_classes: np.ndarray,
    supported: set[str],
) -> dict[str, Any]:
    outer = list(GroupKFold(n_splits=N_SPLITS).split(features, target, groups))
    covered: list[bool] = []
    sizes: list[int] = []
    by_class: dict[str, dict[str, Any]] = {}
    for train, test in outer:
        inner = list(
            GroupKFold(n_splits=N_INNER_SPLITS).split(
                features.iloc[train], target[train], groups[train]
            )
        )
        models: list[HistGradientBoostingClassifier] = []
        inner_scores = np.zeros(len(train))
        inner_fold = np.zeros(len(train), dtype=int)
        for fold, (inner_train, inner_test) in enumerate(inner):
            model = _classifier(features.shape[1]).fit(
                features.iloc[train].iloc[inner_train], target[train][inner_train]
            )
            models.append(model)
            inner_scores[inner_test] = model.predict_proba(
                features.iloc[train].iloc[inner_test]
            )[:, 1]
            inner_fold[inner_test] = fold
        calibration_scores = np.abs(target[train] - inner_scores)
        test_probabilities = np.column_stack(
            [model.predict_proba(features.iloc[test])[:, 1] for model in models]
        )
        for position, row_index in enumerate(test):
            name = material_classes[row_index]
            if name not in supported:
                continue
            included = [
                label
                for label in (0, 1)
                if (
                    1
                    + np.sum(
                        calibration_scores
                        >= np.abs(label - test_probabilities[position])[inner_fold]
                    )
                )
                / (len(train) + 1)
                > CONFORMAL_ALPHA
            ]
            hit = int(target[row_index]) in included
            covered.append(hit)
            sizes.append(len(included))
            bucket = by_class.setdefault(
                name, {"n": 0, "covered": 0, "abstained": 0}
            )
            bucket["n"] += 1
            bucket["covered"] += int(hit)
            bucket["abstained"] += int(len(included) != 1)
    for bucket in by_class.values():
        bucket["coverage"] = round(bucket["covered"] / bucket["n"], 3)
        bucket["abstention_rate"] = round(bucket["abstained"] / bucket["n"], 3)
    return {
        "alpha": CONFORMAL_ALPHA,
        "target_coverage": 1 - CONFORMAL_ALPHA,
        "method": "CV+ over five material-grouped folds",
        "evaluation": "nested GroupKFold(5 outer x 3 inner), supported classes only",
        "coverage": round(float(np.mean(covered)), 3) if covered else None,
        "average_set_size": round(float(np.mean(sizes)), 2) if sizes else None,
        "abstention_rate": round(float(np.mean(np.array(sizes) == 2)), 3)
        if sizes
        else None,
        "evaluated_rows": len(sizes),
        "by_class": by_class,
    }


def _metrics(
    frame: pd.DataFrame,
    features: pd.DataFrame,
    target: np.ndarray,
    groups: np.ndarray,
    oof: np.ndarray,
    splits: list[tuple[np.ndarray, np.ndarray]],
) -> dict[str, Any]:
    classes = sorted(frame["material_class"].unique().tolist())
    medians = {
        "o2_initial_pct": float(pd.to_numeric(frame["o2_initial_pct"], errors="coerce").median()),
        "thickness_mm": float(pd.to_numeric(frame["thickness_mm"], errors="coerce").median()),
    }
    predictions = (oof >= 0.5).astype(int)
    reliability = _reliability(target, oof)
    o2_baseline = _o2_only_auc(frame, target, splits)

    unconstrained_oof = np.zeros(len(frame))
    for train, test in splits:
        model = _classifier(features.shape[1], monotonic=False).fit(
            features.iloc[train], target[train]
        )
        unconstrained_oof[test] = model.predict_proba(features.iloc[test])[:, 1]
    final_unconstrained = _classifier(features.shape[1], monotonic=False).fit(
        features, target
    )
    final_monotonic = _classifier(features.shape[1]).fit(features, target)
    o2_min = float(pd.to_numeric(frame["o2_initial_pct"], errors="coerce").min())
    o2_max = float(pd.to_numeric(frame["o2_initial_pct"], errors="coerce").max())
    unconstrained = {
        "auc": round(float(roc_auc_score(target, unconstrained_oof)), 3),
        "monotonicity_violations": _monotonicity_violations(
            final_unconstrained, classes, medians, o2_min, o2_max
        ),
    }
    monotonic_violations = _monotonicity_violations(
        final_monotonic, classes, medians, o2_min, o2_max
    )

    support = {
        name: int((frame["material_class"] == name).sum()) for name in classes
    }
    positives = {
        name: int(frame.loc[frame["material_class"] == name, "target"].sum())
        for name in classes
    }
    supported = {name for name, count in support.items() if count >= MIN_CLASS_SUPPORT}
    conformal = _conformal_evaluation(
        features,
        target,
        groups,
        frame["material_class"].to_numpy(),
        supported,
    )

    return {
        "n": int(len(frame)),
        "positives": int(target.sum()),
        "negatives": int(len(frame) - target.sum()),
        "positive_rate": round(float(target.mean()), 3),
        "target_threshold_delta_co2_pct": TARGET_THRESHOLD,
        "features": list(FEATURES),
        "o2_median_pct": round(medians["o2_initial_pct"], 2),
        "thickness_median_mm": round(medians["thickness_mm"], 3),
        "auc": round(float(roc_auc_score(target, oof)), 3),
        "o2_only_auc": round(o2_baseline, 3),
        "unconstrained": unconstrained,
        "brier": round(float(brier_score_loss(target, oof)), 3),
        "ece": reliability["ece"],
        "reliability": reliability["bins"],
        "accuracy": round(float(accuracy_score(target, predictions)), 3),
        "balanced_accuracy": round(
            float(balanced_accuracy_score(target, predictions)), 3
        ),
        "f1": round(float(f1_score(target, predictions)), 3),
        "majority_baseline_accuracy": round(
            max(float(target.mean()), 1.0 - float(target.mean())), 3
        ),
        "split": "GroupKFold(5) grouped by material description",
        "monotonic": {
            "feature": "o2_initial_pct",
            "direction": "non-decreasing",
            "violations": monotonic_violations,
            "reason": "Higher oxygen cannot reduce CO2 rise; the constraint is a physical prior.",
        },
        "support": support,
        "positives_by_class": positives,
        "min_class_support": MIN_CLASS_SUPPORT,
        "supported_classes": sorted(supported),
        "excluded_classes": sorted(set(classes) - supported),
        "o2_support": [o2_min, o2_max],
        "conformal": conformal,
        "scope": "BASS-II PMMA/SIBAL/Nomex/Other; predicts CO2-rise severity, not flammability.",
        "model": "monotonic histogram gradient boosting",
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
    classes = sorted(frame["material_class"].unique().tolist())
    medians = {
        "o2_initial_pct": float(pd.to_numeric(frame["o2_initial_pct"], errors="coerce").median()),
        "thickness_mm": float(pd.to_numeric(frame["thickness_mm"], errors="coerce").median()),
    }
    features = _design_matrix(frame, classes, medians)
    target = frame["target"].to_numpy()
    groups = frame["material"].to_numpy()
    fold_models, oof, fold_of, splits = _fit_folds(features, target, groups)
    metrics = _metrics(frame, features, target, groups, oof, splits)
    metrics["gate"] = {
        "auc_min": 0.75,
        "auc_beats_o2_only": True,
        "monotonic_violations_max": 0,
        "passed": metrics["auc"] >= 0.75
        and metrics["auc"] > metrics["o2_only_auc"]
        and metrics["monotonic"]["violations"] == 0,
    }
    payload = {
        "models": fold_models,
        "classes": classes,
        "medians": medians,
        "frame": frame,
        "oof": oof,
        "fold_of": fold_of,
        "metrics": metrics,
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


def _support_payload(metrics: dict[str, Any], name: str) -> dict[str, Any]:
    return {
        "class_rows": int(metrics["support"].get(name, 0)),
        "class_positives": int(metrics["positives_by_class"].get(name, 0)),
        "min_rows": int(metrics["min_class_support"]),
        "o2_min": metrics["o2_support"][0],
        "o2_max": metrics["o2_support"][1],
        "total_rows": metrics["n"],
    }


def predict_severity(
    connection: sqlite3.Connection,
    material: str,
    o2_pct: float,
    thickness_mm: float | None = None,
) -> dict[str, Any]:
    payload = get_model(connection)
    metrics = payload["metrics"]
    query_class = material_class(material)
    support = _support_payload(metrics, query_class)
    base: dict[str, Any] = {
        "material_class": query_class,
        "support": support,
        "metrics": metrics,
        "caveat": (
            "Within-BASS-II CO₂-rise screen; not a flammability, ignition, or flight-approval prediction. "
            "The evidence grade is assigned by deterministic rules, not this model."
        ),
    }
    if query_class not in payload["classes"]:
        return {
            **base,
            "enabled": False,
            "status": "unseen_class",
            "band": None,
            "probability_delta_co2_gt_0.5": None,
            "reason": f"Unseen material class '{query_class}' for the BASS-II severity model.",
        }
    if support["class_rows"] < support["min_rows"]:
        return {
            **base,
            "enabled": False,
            "status": "low_support",
            "band": None,
            "probability_delta_co2_gt_0.5": None,
            "reason": (
                f"{query_class} has {support['class_rows']} BASS-II training rows; "
                f"the minimum is {support['min_rows']}."
            ),
        }
    if not (support["o2_min"] <= float(o2_pct) <= support["o2_max"]):
        nearest = min(max(float(o2_pct), support["o2_min"]), support["o2_max"])
        return {
            **base,
            "enabled": False,
            "status": "outside_support",
            "band": None,
            "probability_delta_co2_gt_0.5": None,
            "nearest_supported_o2": nearest,
            "reason": (
                f"{o2_pct}% O₂ is outside the BASS-II training range "
                f"({support['o2_min']}–{support['o2_max']}%)."
            ),
        }
    query = pd.DataFrame(
        [
            {
                "o2_initial_pct": float(o2_pct),
                "thickness_mm": thickness_mm,
                "material_class": query_class,
            }
        ]
    )
    matrix = _design_matrix(query, payload["classes"], payload["medians"])
    fold_probabilities = np.array(
        [model.predict_proba(matrix)[0, 1] for model in payload["models"]]
    )
    probability = float(fold_probabilities.mean())
    calibration_scores = np.abs(payload["frame"]["target"].to_numpy() - payload["oof"])
    included = [
        label
        for label in (0, 1)
        if (
            1
            + np.sum(
                calibration_scores
                >= np.abs(label - fold_probabilities[payload["fold_of"]])
            )
        )
        / (len(calibration_scores) + 1)
        > CONFORMAL_ALPHA
    ]
    labels = {0: "low", 1: "high"}
    set_labels = [labels[label] for label in included]
    band = labels[included[0]] if len(included) == 1 else "indeterminate"
    return {
        **base,
        "enabled": True,
        "status": "resolved" if len(included) == 1 else "indeterminate",
        "probability_delta_co2_gt_0.5": round(probability, 3),
        "band": band,
        "conformal": {
            "alpha": CONFORMAL_ALPHA,
            "confidence": 1 - CONFORMAL_ALPHA,
            "set": included,
            "labels": set_labels,
            "target_coverage": metrics["conformal"]["target_coverage"],
            "coverage": metrics["conformal"]["coverage"],
            "average_set_size": metrics["conformal"]["average_set_size"],
        },
        "thickness_imputed": thickness_mm is None or pd.isna(thickness_mm),
    }
