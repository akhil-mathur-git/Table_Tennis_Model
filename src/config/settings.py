from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"

RAW_DIR = DATA_DIR / "raw"
RAW_BETSAPI_DIR = RAW_DIR / "betsapi"
RAW_ENDED_EVENTS_DIR = RAW_BETSAPI_DIR / "ended_events"
RAW_EVENT_VIEWS_DIR = RAW_BETSAPI_DIR / "event_views"

PROCESSED_DIR = DATA_DIR / "processed"
DAILY_DIR = PROCESSED_DIR / "daily"
VALIDATION_DIR = PROCESSED_DIR / "validation"
CLEANED_DIR = PROCESSED_DIR / "cleaned"
COMBINED_DIR = PROCESSED_DIR / "combined"

SPORT_ID_TABLE_TENNIS = 92

TAB_LEAGUES = [
    "TT Cup",
    "TT Elite Series",
    "Czech Liga Pro",
]

MAX_EVENT_IDS_PER_VIEW_REQUEST = 10
REQUEST_DELAY_SECONDS = 0.2

KEEP_ONLY_SETS_1_TO_5 = True


def ensure_data_dirs():
    folders = [
        RAW_ENDED_EVENTS_DIR,
        RAW_EVENT_VIEWS_DIR,
        DAILY_DIR,
        VALIDATION_DIR,
        CLEANED_DIR,
        COMBINED_DIR,
    ]

    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)