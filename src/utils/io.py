import json
from pathlib import Path

import pandas as pd


def save_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def load_json(path):
    path = Path(path)

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_dataframe(df, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def load_dataframe(path):
    return pd.read_csv(path)