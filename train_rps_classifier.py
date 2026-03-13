# train_rps_classifier.py
from __future__ import annotations
from pathlib import Path
import numpy as np
from PIL import Image

import tensorflow as tf
from tensorflow.keras import layers, models

DATA_DIR = Path(r"cv_src\prof\HandPhotos\Testing")
OUT_DIR = Path("cv_models")
OUT_DIR.mkdir(exist_ok=True)
OUT_PATH = OUT_DIR / "rps_classifier.h5"

LABEL_MAP = {"rock": 0, "paper": 1, "scissors": 2}
CLASS_NAMES = ["rock", "paper", "scissors"]

IMG_SIZE = (128, 128)  # small so it trains fast

def load_dataset():
    X, y = [], []
    for p in sorted(DATA_DIR.glob("*.png")):
        name = p.name.lower()
        label = None
        for k in LABEL_MAP:
            if name.startswith(k + "_"):
                label = LABEL_MAP[k]
                break
        if label is None:
            continue

        img = Image.open(p).convert("RGB").resize(IMG_SIZE)
        arr = np.asarray(img, dtype=np.float32) / 255.0
        X.append(arr)
        y.append(label)

    X = np.stack(X, axis=0)
    y = np.array(y, dtype=np.int32)
    return X, y

X, y = load_dataset()
print("Loaded:", X.shape, y.shape, "labels:", y.tolist())

# very small model (works for smoke test)
model = models.Sequential([
    layers.Input(shape=(IMG_SIZE[0], IMG_SIZE[1], 3)),
    layers.Conv2D(16, 3, activation="relu"),
    layers.MaxPooling2D(),
    layers.Conv2D(32, 3, activation="relu"),
    layers.MaxPooling2D(),
    layers.Flatten(),
    layers.Dense(64, activation="relu"),
    layers.Dense(3, activation="softmax"),
])

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

# train (overfit is fine for now)
model.fit(X, y, epochs=25, batch_size=2, verbose=1)

model.save(OUT_PATH)
print("Saved model to:", OUT_PATH)