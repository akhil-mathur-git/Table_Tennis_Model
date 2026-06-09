import os
from datetime import datetime, timedelta
from pprint import pprint

import requests
from dotenv import load_dotenv


# BetsAPI sport ID for table tennis
SPORT_ID_TABLE_TENNIS = 92


def chunk_list(items, chunk_size):
    """
    Splits a list into smaller chunks.

    Example:
    items = [1, 2, 3, 4, 5]
    chunk_size = 2

    returns:
    [[1, 2], [3, 4], [5]]
    """
    chunks = []

    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        chunks.append(chunk)

    return chunks


# 1. Load your private API token from .env
load_dotenv()

token = os.getenv("BETS_API_TOKEN")

if not token:
    raise ValueError("BETS_API_TOKEN is missing. Check your .env file.")


# 2. Choose the historical date we want to test
# For now, we use yesterday because the matches should be finished.
day = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

print(f"Testing historical table tennis data for: {day}")


# 3. Get ended table tennis events for that date
ended_url = "https://api.b365api.com/v3/events/ended"

ended_params = {
    "token": token,
    "sport_id": SPORT_ID_TABLE_TENNIS,
    "day": day,
}

ended_response = requests.get(ended_url, params=ended_params, timeout=20)

print("\nEnded events status code:", ended_response.status_code)

ended_response.raise_for_status()

ended_data = ended_response.json()

print("\nEnded events top-level keys:")
print(ended_data.keys())


# 4. Extract the list of completed matches
events = ended_data.get("results", [])

print(f"\nNumber of ended table tennis events found: {len(events)}")


if not events:
    print("\nNo ended events found for this date. Try changing the date manually.")
    exit()


# 5. Print the first completed match summary so we understand the raw data
print("\nFirst ended event summary:")
pprint(events[0])


# 6. Collect event IDs from all ended matches
event_ids = [event["id"] for event in events]

print("\nFirst 10 event IDs:")
print(event_ids[:10])


# 7. Split event IDs into batches of 10
# This keeps our request count low.
event_id_batches = chunk_list(event_ids, 10)

print(f"\nNumber of event/view batches needed: {len(event_id_batches)}")


# 8. Request detailed data for each batch of event IDs
view_url = "https://api.b365api.com/v1/event/view"

total_detailed_events = 0
events_with_timeline = []

for batch_number, batch in enumerate(event_id_batches, start=1):
    print(f"\nRequesting batch {batch_number}/{len(event_id_batches)}")

    view_params = {
        "token": token,
        "event_id": ",".join(batch),
    }

    view_response = requests.get(view_url, params=view_params, timeout=20)

    print("Status code:", view_response.status_code)

    view_response.raise_for_status()

    view_data = view_response.json()

    detailed_events = view_data.get("results", [])

    total_detailed_events += len(detailed_events)

    for event in detailed_events:
        timeline = event.get("timeline", [])

        if timeline:
            events_with_timeline.append(event)

        event_id = event.get("id")
        home_name = event.get("home", {}).get("name")
        away_name = event.get("away", {}).get("name")
        league_name = event.get("league", {}).get("name")
        final_score = event.get("ss")
        timeline_length = len(timeline)

        print(
            f"{event_id}: {home_name} vs {away_name} | "
            f"{league_name} | final score: {final_score} | "
            f"timeline length: {timeline_length}"
        )


# 9. Summarise what we found
print("\nSummary:")
print("Total detailed events checked:", total_detailed_events)
print("Events with non-empty timeline:", len(events_with_timeline))


# 10. If we found a match with timeline data, print an example
if events_with_timeline:
    example = events_with_timeline[0]

    print("\nExample event with timeline:")
    print("ID:", example.get("id"))
    print("League:", example.get("league", {}).get("name"))
    print("Home:", example.get("home", {}).get("name"))
    print("Away:", example.get("away", {}).get("name"))
    print("Final match score:", example.get("ss"))

    print("\nSet scores:")
    pprint(example.get("scores"))

    timeline = example.get("timeline", [])

    print("\nFirst 10 timeline entries:")
    pprint(timeline[:10])

    print("\nLast 10 timeline entries:")
    pprint(timeline[-10:])

else:
    print("\nNo non-empty timelines found in these events.")
    print("This does not fully prove BetsAPI has no historical timeline data.")
    print("Next tests would be:")
    print("- try another date")
    print("- try a different league")
    print("- test event/view on a live match")
    print("- check if a different endpoint is needed for point-by-point data")