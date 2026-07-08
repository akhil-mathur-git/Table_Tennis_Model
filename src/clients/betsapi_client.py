import os
import time

import requests
from dotenv import load_dotenv

from src.config.settings import (
    PROJECT_ROOT,
    REQUEST_DELAY_SECONDS,
    SPORT_ID_TABLE_TENNIS,
)


class BetsAPIClient:
    def __init__(self):
        load_dotenv(PROJECT_ROOT / ".env")

        token = os.getenv("BETS_API_TOKEN")

        if not token:
            raise ValueError("BETS_API_TOKEN is missing. Check your .env file.")

        self.token = token
        self.session = requests.Session()

    def _get_json(self, url, params):
        response = self.session.get(url, params=params, timeout=20)

        print("Status code:", response.status_code)

        response.raise_for_status()

        time.sleep(REQUEST_DELAY_SECONDS)

        return response.json()

    def get_ended_events_page(self, day, page):
        url = "https://api.b365api.com/v3/events/ended"

        params = {
            "token": self.token,
            "sport_id": SPORT_ID_TABLE_TENNIS,
            "day": day,
            "page": page,
        }

        return self._get_json(url, params)

    def get_event_views(self, event_ids):
        url = "https://api.b365api.com/v1/event/view"

        params = {
            "token": self.token,
            "event_id": ",".join(event_ids),
        }

        return self._get_json(url, params)