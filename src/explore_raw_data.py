from pathlib import Path
import json
from pprint import pprint


PROJECT_ROOT = Path(__file__).resolve().parents[1]

batch_path = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "betsapi"
    / "event_views"
    / "20260601"
    / "batch_001.json"
)

with open(batch_path,"r", encoding="utf-8") as file:
    data = json.load(file)



matches = data["results"]
first_match = matches[3]
print(type(first_match))

print(first_match.keys())

for key, value in first_match.items():
    if key != "timeline":
        print(f"\n{key}:")
        pprint(value)

timeline = first_match["timeline"]

print("\nTimeline length:")
print(len(timeline))

print("\nFirst 10 timeline rows:")
pprint(timeline[:10])

print("\nKeys in first timeline row:")
print(timeline[0].keys())