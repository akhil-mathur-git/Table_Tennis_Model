import os
from pprint import pprint

import requests
from dotenv import load_dotenv


def main():
    # Loads private variables from the .env file
    load_dotenv()

    token = os.getenv("BETS_API_TOKEN")

    if not token:
        raise ValueError("BETS_API_TOKEN is missing. Add it to your .env file.")

    # Table tennis sport_id is 92 in BetsAPI
    url = "https://api.b365api.com/v3/events/inplay"

    params = {
        "sport_id": 92,
        "token": token,
    }

    response = requests.get(url, params=params, timeout=20)

    print("Status code:", response.status_code)

    # If the request failed, this will show the error clearly
    response.raise_for_status()

    data = response.json()

    print("\nTop-level response keys:")
    print(data.keys())

    events = data.get("results", [])

    print(f"\nNumber of live table tennis events found: {len(events)}")

    if len(events) == 0:
        print("\nNo live table tennis events right now. That is okay.")
        print("The API connection still worked if the status code was 200.")
        return

    print("\nFirst event:")
    pprint(events[0])


if __name__ == "__main__":
    main()