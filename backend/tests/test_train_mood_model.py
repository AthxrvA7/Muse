"""The training script runs end to end on a tiny dataset (no download)."""

import csv
import json
from pathlib import Path

import joblib

from scripts.train_mood_model import CARD_FILE, MODEL_FILE, main, sha256_of

SAMPLES = {
    "joy": ["what a great day", "so happy right now", "feeling wonderful and glad"],
    "sadness": ["i feel so sad", "everything is gloomy", "feeling down and empty"],
    "anger": ["i am so angry", "this makes me furious", "really mad about it"],
    "fear": ["i am scared", "feeling nervous and afraid", "so worried about tomorrow"],
    "love": ["i love you so much", "feeling loved and warm", "my heart is full of love"],
    "surprise": ["wow i did not expect that", "totally amazed", "what a shock"],
}


def _write_csv(path: Path, repeat: int) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["text", "label"])
        for label, texts in SAMPLES.items():
            for _ in range(repeat):
                for text in texts:
                    writer.writerow([text, label])


def test_training_writes_model_and_card(tmp_path: Path) -> None:
    data_dir, out_dir = tmp_path / "data", tmp_path / "out"
    data_dir.mkdir()
    _write_csv(data_dir / "train.csv", repeat=6)
    _write_csv(data_dir / "test.csv", repeat=1)

    main(["--csv-dir", str(data_dir), "--out-dir", str(out_dir)])

    model_path, card_path = out_dir / MODEL_FILE, out_dir / CARD_FILE
    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert card["sha256"] == sha256_of(model_path)
    assert card["labels"] == sorted(SAMPLES)
    assert 0 <= card["metrics"]["test_macro_f1"] <= 1

    model = joblib.load(model_path)
    assert model.predict(["so happy right now"])[0] == "joy"
