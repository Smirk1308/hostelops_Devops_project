# ml/ — Synthetic Data and ML Models for HostelOps

## What is the data?

`ml/data/complaints.csv` is **synthetic sample data** created for the HostelOps project demonstration.
It is **NOT** real hostel complaint data. It was generated deterministically by `ml/generate_data.py`
using hand-written sentence templates with varied place and time fillers.

> **Important Note on Performance:**
> A high score on synthetic held-out validation data indicates strong template separation,
> but does **not** establish equivalent accuracy on real, noisy human-written complaints.
> This model is designed for demo and triage suggestion assistance, not production-grade automation.

## Dataset Structure

- **Columns**: `text`, `category`, `priority`
- **Total rows**: 350 samples (~50 per category)
- **Categories (7)**: `Water`, `Electricity`, `Wi-Fi`, `Mess`, `Cleanliness`, `Furniture`, `Other`
- **Priorities (3)**: `Low`, `Medium`, `High`
- **Deduplication**: 100% unique complaint descriptions (no duplicate texts)

## How to regenerate the dataset

```bash
python -m ml.generate_data
```

This writes `ml/data/complaints.csv` deterministically using `random.Random(42)`.

## How to train the models

```bash
python -m ml.train
```

This reads the CSV and saves the trained pipelines to `ml/model.joblib`.
`ml/model.joblib` is gitignored and is generated automatically during Docker image build.

## What the two models predict

| Pipeline | Features | Algorithm | Output |
|---|---|---|---|
| **category** | TF-IDF (1, 2) n-grams | LogisticRegression(max_iter=1000) | 1 of 7 categories |
| **priority** | TF-IDF (1, 2) n-grams | LogisticRegression(max_iter=1000) | 1 of 3 priorities (`Low`, `Medium`, `High`) |

Both pipelines are evaluated on an 80/20 stratified split (`random_state=42`), consistently achieving held-out accuracies above 0.80.
