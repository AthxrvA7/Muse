"""Train Muse's free-text mood classifier.

Model:   TF-IDF (words + word pairs) -> logistic regression, 6 emotions.
Data:    dair-ai/emotion (Saravia et al., 2018, "CARER"), English, 6 emotions,
         licensed for educational and research use. No Spotify data is used.
Output:  app/knowledge/mood_model.joblib       the trained pipeline
         app/knowledge/mood_model_card.json    what it is, how good it is, its SHA-256

Usage (from backend/, with requirements-train.txt installed):
    python -m scripts.train_mood_model                    # download dataset and train
    python -m scripts.train_mood_model --parquet-dir DIR  # use files you downloaded yourself
    python -m scripts.train_mood_model --csv-dir DIR      # train.csv + test.csv (text,label)
"""

import argparse
import csv
import hashlib
import json
import platform
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import Pipeline

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = BACKEND_DIR / "app" / "knowledge"
MODEL_FILE = "mood_model.joblib"
CARD_FILE = "mood_model_card.json"

DATASET = "dair-ai/emotion"
DATASET_URL = "https://huggingface.co/datasets/dair-ai/emotion"
PARQUET_URL = DATASET_URL + "/resolve/main/split/{split}-00000-of-00001.parquet"
# Label order as published on the dataset card (label 0 = sadness, ...)
LABELS = ["sadness", "joy", "love", "anger", "fear", "surprise"]

# Regularisation strengths tried; the best one on the validation split is kept
C_VALUES = [0.5, 1.0, 2.0, 4.0, 8.0]
SEED = 42

Split = tuple[list[str], list[str]]  # (texts, labels)


# ---------- loading data ----------


def load_parquet(source: str, split: str) -> Split:
    import pandas as pd  # only needed for the real dataset

    frame = pd.read_parquet(source)
    labels = [LABELS[i] for i in frame["label"]]
    print(f"  {split}: {len(frame)} rows")
    return frame["text"].tolist(), labels


def load_csv(path: Path) -> Split:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [r["text"] for r in rows], [r["label"] for r in rows]


def split_off(data: Split, share: float) -> tuple[Split, Split]:
    """Hold back a random share of rows (for validation when none is given)."""
    pairs = list(zip(*data, strict=True))
    random.Random(SEED).shuffle(pairs)  # noqa: S311 - reproducible data split, not security
    cut = int(len(pairs) * (1 - share))
    keep, held = pairs[:cut], pairs[cut:]
    return ([t for t, _ in keep], [y for _, y in keep]), (
        [t for t, _ in held],
        [y for _, y in held],
    )


def load_dataset(args: argparse.Namespace) -> dict[str, Split]:
    if args.csv_dir:
        train = load_csv(args.csv_dir / "train.csv")
        test = load_csv(args.csv_dir / "test.csv")
        val_path = args.csv_dir / "validation.csv"
        if val_path.exists():
            return {"train": train, "validation": load_csv(val_path), "test": test}
        train, validation = split_off(train, 0.1)
        return {"train": train, "validation": validation, "test": test}

    print(f"Loading {DATASET} ...")
    data = {}
    for split in ("train", "validation", "test"):
        if args.parquet_dir:
            source = str(args.parquet_dir / f"{split}-00000-of-00001.parquet")
        else:
            source = PARQUET_URL.format(split=split)
        data[split] = load_parquet(source, split)
    return data


# ---------- training ----------


def build_pipeline(c: float) -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),  # single words and word pairs ("not happy")
                    min_df=2,  # ignore words seen only once
                    max_features=30_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(C=c, max_iter=2000, class_weight="balanced"),
            ),
        ]
    )


def train(data: dict[str, Split]) -> tuple[Pipeline, dict[str, Any]]:
    train_x, train_y = data["train"]
    val_x, val_y = data["validation"]

    scores = {}
    for c in C_VALUES:
        candidate = build_pipeline(c).fit(train_x, train_y)
        scores[c] = f1_score(val_y, candidate.predict(val_x), average="macro")
        print(f"  C={c:<4} validation macro-F1 = {scores[c]:.3f}")
    best_c = max(scores, key=lambda c: scores[c])

    # Final model: best setting, trained on train + validation
    model = build_pipeline(best_c).fit(train_x + val_x, train_y + val_y)

    test_x, test_y = data["test"]
    predicted = model.predict(test_x)
    metrics = {
        "best_C": best_c,
        "validation_macro_f1": round(scores[best_c], 4),
        "test_accuracy": round(accuracy_score(test_y, predicted), 4),
        "test_macro_f1": round(f1_score(test_y, predicted, average="macro"), 4),
        "train_rows": len(train_x) + len(val_x),
        "test_rows": len(test_x),
    }
    print(classification_report(test_y, predicted, digits=3))
    return model, metrics


# ---------- saving ----------


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(model: Pipeline, metrics: dict[str, Any], out_dir: Path, dataset: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / MODEL_FILE
    joblib.dump(model, model_path, compress=3)

    card = {
        "name": "muse-mood-classifier",
        "model": "TF-IDF (1-2 word n-grams) + logistic regression",
        "labels": sorted(model.classes_.tolist()),
        "dataset": dataset,
        "dataset_terms": "educational and research use only",
        "intended_use": "Map a short English mood sentence to one of 6 emotions for music "
        "curation. Not a diagnostic or mental-health tool.",
        "limitations": "English only; trained on short social-media sentences; misses sarcasm "
        "and indirect phrasing.",
        "metrics": metrics,
        "sha256": sha256_of(model_path),
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    card_path = out_dir / CARD_FILE
    card_path.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    size_mb = model_path.stat().st_size / 1e6
    print(f"Saved {model_path.name} ({size_mb:.1f} MB) and {card_path.name}")
    return model_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--parquet-dir", type=Path, help="folder with the dataset's parquet files")
    source.add_argument("--csv-dir", type=Path, help="folder with train.csv and test.csv")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    data = load_dataset(args)
    print("Training ...")
    model, metrics = train(data)
    dataset = f"{DATASET} ({DATASET_URL})" if not args.csv_dir else f"local CSV: {args.csv_dir}"
    save(model, metrics, args.out_dir, dataset)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
