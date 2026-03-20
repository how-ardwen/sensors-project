from pathlib import Path
import cv_bridge

base = Path(r"cv_src\prof\HandPhotos\Testing")
tests = [
    base / "rock_01.png",
    base / "paper_01.png",
    base / "scissors_01.png",
]

for p in tests:
    pred, conf = cv_bridge.classify_image_file(p)
    print(p.name, "->", pred, f"(conf={conf:.2f})")