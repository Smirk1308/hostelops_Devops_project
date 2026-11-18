"""ML model loader and suggestion helper for triage.

Loads a joblib model dict keyed by resolved path + mtime so a retrained
model is picked up automatically without restarting the server.
"""
import os
import pathlib

import joblib

# Cache: {(path_str, mtime_float): model_dict}
_CACHE = {}

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]


def clear_cache():
    """Empty the model cache (used in tests)."""
    _CACHE.clear()


def _resolve_path(path=None):
    """Return an absolute Path for the model file."""
    if path is None:
        try:
            from flask import current_app
            path = current_app.config.get('MODEL_PATH', 'ml/model.joblib')
        except RuntimeError:
            path = os.environ.get('MODEL_PATH', 'ml/model.joblib')

    p = pathlib.Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def load_model(path=None):
    """Load and cache the joblib model dict.

    Returns the model dict or None if the file is missing or unloadable.
    """
    p = _resolve_path(path)
    if not p.exists():
        return None

    try:
        mtime = p.stat().st_mtime
    except OSError:
        return None

    cache_key = (str(p), mtime)
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    try:
        model = joblib.load(p)
    except Exception:
        return None

    _CACHE[cache_key] = model
    return model


def suggest(text, model_path=None):
    """Predict category and priority for a complaint text.

    Returns (category, priority, confidence).
    Returns (None, None, 0.0) for blank/short input or missing model.
    """
    if not isinstance(text, str) or not text.strip() or len(text.strip()) < 5:
        return (None, None, 0.0)

    model = load_model(model_path)
    if model is None:
        return (None, None, 0.0)

    try:
        cat_pipe = model['category']
        pri_pipe = model['priority']

        category = str(cat_pipe.predict([text])[0])
        priority = str(pri_pipe.predict([text])[0])

        # Confidence = max predicted probability from category pipeline
        proba = cat_pipe.predict_proba([text])[0]
        confidence = round(float(proba.max()), 3)

        return (category, priority, confidence)
    except Exception:
        return (None, None, 0.0)
