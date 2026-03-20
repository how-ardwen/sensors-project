# cv_bridge.py
from __future__ import annotations
from pathlib import Path
from typing import Tuple
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model

REPO_ROOT = Path(__file__).resolve().parent
MODEL_PATH = REPO_ROOT / "cv_models" / "rps_classifier.h5"
IMG_SIZE = (128, 128)
CLASS_NAMES = ["rock", "paper", "scissors"]
_TO_RPS = {"rock": "R", "paper": "P", "scissors": "S"}

_model = None

def _get_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
        _model = load_model(str(MODEL_PATH))
    return _model

def classify_image_file(image_path: str | Path) -> Tuple[str, float]:
    """
    Returns ('R'|'P'|'S', confidence) for a single image file.
    """
    model = _get_model()
    img = Image.open(image_path).convert("RGB").resize(IMG_SIZE)
    x = np.asarray(img, dtype=np.float32) / 255.0
    x = np.expand_dims(x, axis=0)  # (1,H,W,3)
    probs = model.predict(x, verbose=0)[0]
    idx = int(np.argmax(probs))
    cls = CLASS_NAMES[idx]
    conf = float(probs[idx])
    return _TO_RPS[cls], conf

def detect_stage1_from_files(left_img: str | Path, right_img: str | Path) -> Tuple[str, str]:
    l, _ = classify_image_file(left_img)
    r, _ = classify_image_file(right_img)
    return l, r

def detect_stage2_from_file(kept_img: str | Path) -> str:
    k, _ = classify_image_file(kept_img)
    return k