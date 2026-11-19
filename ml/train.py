"""Training script for HostelOps triage ML models.

Trains two Pipelines (category and priority predictors) on the synthetic
complaints CSV and saves them together as a single joblib file.

Run with: python -m ml.train
"""
import pathlib

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

# Paths resolved from the project root so they work from any cwd
_HERE = pathlib.Path(__file__).resolve()
PROJECT_ROOT = _HERE.parents[1]

DEFAULT_CSV = PROJECT_ROOT / 'ml' / 'data' / 'complaints.csv'
DEFAULT_MODEL = PROJECT_ROOT / 'ml' / 'model.joblib'


def _build_pipeline():
    """Return a fresh TF-IDF + LogisticRegression pipeline."""
    return Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
        ('clf', LogisticRegression(max_iter=1000)),
    ])


def _split_and_fit(X, y, label):
    """Split data, fit a pipeline, and return (pipeline, accuracy)."""
    # Fall back to no-stratify when a class is too small to stratify
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

    pipe = _build_pipeline()
    pipe.fit(X_train, y_train)
    acc = pipe.score(X_test, y_test)
    print(f'  {label} accuracy: {acc:.4f}')
    return pipe, float(acc)


def train(csv_path=DEFAULT_CSV, model_path=DEFAULT_MODEL):
    """Train category and priority models; save to model_path.

    Returns a dict with 'category_accuracy' and 'priority_accuracy'.
    """
    csv_path = pathlib.Path(csv_path)
    model_path = pathlib.Path(model_path)

    df = pd.read_csv(csv_path)
    X = df['text'].astype(str)

    category_pipe, cat_acc = _split_and_fit(X, df['category'], 'category')
    priority_pipe, pri_acc = _split_and_fit(X, df['priority'], 'priority')

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({'category': category_pipe, 'priority': priority_pipe}, model_path)
    print(f'  Model saved to {model_path}')

    return {
        'category_accuracy': cat_acc,
        'priority_accuracy': pri_acc,
    }


if __name__ == '__main__':
    print('Training HostelOps triage models...')
    result = train()
    print(f"category_accuracy: {result['category_accuracy']:.4f}")
    print(f"priority_accuracy: {result['priority_accuracy']:.4f}")
