# ADR-0005: TF-IDF + logistic regression mood classifier

- **Status:** Accepted · **Date:** 2026-10-20

## Context
FR5 requires turning free-text mood into musical characteristics. The synopsis specifies scikit-learn. The model must start fast in a small container and be explainable.

## Decision
Train a TF-IDF (word + character n-grams) + multinomial logistic regression model offline on a public English emotion dataset (6 classes), via `scripts/train_mood_model.py`. Save it as a versioned `.joblib` file with a recorded SHA-256 hash, accuracy and macro-F1. At runtime, emotion probabilities are mapped to valence/energy using Russell's circumplex coordinates. Chips are weighted above text.

## Alternatives considered
- **Transformer models (e.g. DistilRoBERTa emotion):** better accuracy, but a ~300 MB+ image, slow cold starts on the free tier, and beyond what the synopsis promises. Kept as a future experiment.
- **LLM API:** rejected. It costs money, sends mood text to a third party (privacy) and is non-deterministic.
- **Lexicon only (e.g. NRC):** rejected as the primary method because of its non-commercial licence and weaker accuracy; keyword rules are kept only as a fallback.

## Consequences
- Small (a few MB), fast (< 10 ms per call) and deterministic.
- English only; misses sarcasm and indirect phrasing. Documented as a limitation.
- The model is trained on public non-Spotify data, so it is compliant with Spotify's terms.
