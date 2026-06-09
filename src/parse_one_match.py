import os
from datetime import datetime, timedelta
from pathlib import Path
from pprint import pprint

import pandas as pd
import requests
from dotenv import load_dotenv


SPORT_ID_TABLE_TENNIS = 92
MAX_EVENT_IDS_PER_VIEW_REQUEST = 10


def chunk_list(items, chunk_size):
    """
    Splits a list into smaller chunks.

    Example:
    [1, 2, 3, 4, 5] with chunk_size = 2
    becomes [[1, 2], [3, 4], [5]]
    """
    chunks = []

    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        chunks.append(chunk)

    return chunks


def parse_score(score_string):
    """
    Converts a score string like '7-5' into two integers.

    Example:
    '7-5' becomes 7, 5
    """
    home_score, away_score = score_string.split("-")
    return int(home_score), int(away_score)


def get_set_winner(event, set_number):
    """
    Uses the final set score to determine who won the set.

    Example:
    Set score:
    home 11, away 7

    returns:
    'home'
    """
    scores = event.get("scores", {})

    set_score = scores.get(str(set_number))

    if set_score is None:
        return None

    home_final_points = int(set_score["home"])
    away_final_points = int(set_score["away"])

    if home_final_points > away_final_points:
        return "home"
    else:
        return "away"


def get_match_winner(event):
    """
    Uses final match score like '3-1' or '1-3' to determine match winner.
    """
    final_match_score = event.get("ss")

    if final_match_score is None:
        return None

    home_sets, away_sets = parse_score(final_match_score)

    if home_sets > away_sets:
        return "home"
    else:
        return "away"


def point_winner_from_te(te_value):
    """
    In BetsAPI timeline:
    te = '0' means home scored the point
    te = '1' means away scored the point
    """
    if te_value == "0":
        return "home"
    elif te_value == "1":
        return "away"
    else:
        return None


def parse_event_to_score_state_rows(event):
    """
    Converts one BetsAPI table tennis event into clean score-state rows.

    One row = one score state after a point is played.
    """
    rows = []

    match_id = event.get("id")
    league_name = event.get("league", {}).get("name")
    home_player = event.get("home", {}).get("name")
    away_player = event.get("away", {}).get("name")
    final_match_score = event.get("ss")
    match_winner = get_match_winner(event)

    timeline = event.get("timeline", [])

    for point_number, timeline_entry in enumerate(timeline, start=1):
        set_number = int(timeline_entry["gm"])
        score_state = timeline_entry["ss"]
        te_value = timeline_entry.get("te")

        home_points, away_points = parse_score(score_state)

        point_winner = point_winner_from_te(te_value)
        set_winner = get_set_winner(event, set_number)

        if set_winner is None:
            continue

        home_won_set = 1 if set_winner == "home" else 0
        home_won_match = 1 if match_winner == "home" else 0

        point_difference = home_points - away_points
        total_points_played = home_points + away_points

        if home_points > away_points:
            leader = "home"
            leader_points = home_points
            trailer_points = away_points
            leader_won_set = 1 if set_winner == "home" else 0
        elif away_points > home_points:
            leader = "away"
            leader_points = away_points
            trailer_points = home_points
            leader_won_set = 1 if set_winner == "away" else 0
        else:
            leader = "tie"
            leader_points = home_points
            trailer_points = away_points
            leader_won_set = None

        row = {
            "match_id": match_id,
            "league": league_name,
            "home_player": home_player,
            "away_player": away_player,
            "final_match_score": final_match_score,
            "match_winner": match_winner,

            "set_number": set_number,
            "point_number_in_match": point_number,
            "score_state": score_state,
            "home_points": home_points,
            "away_points": away_points,
            "point_winner": point_winner,

            "set_winner": set_winner,
            "home_won_set": home_won_set,
            "home_won_match": home_won_match,

            "point_difference": point_difference,
            "total_points_played": total_points_played,

            "leader": leader,
            "leader_points": leader_points,
            "trailer_points": trailer_points,
            "leader_won_set": leader_won_set,
        }

        rows.append(row)

    return rows


def get_ended_events(token, day):
    """
    Gets completed table tennis matches for one date.
    """
    url = "https://api.b365api.com/v3/events/ended"

    params = {
        "token": token,
        "sport_id": SPORT_ID_TABLE_TENNIS,
        "day": day,
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()
    return data.get("results", [])


def get_event_views(token, event_ids):
    """
    Gets detailed event data for a list of event IDs.

    BetsAPI lets us request multiple event IDs at once.
    We will request them in batches of 10.
    """
    url = "https://api.b365api.com/v1/event/view"

    all_detailed_events = []

    event_id_batches = chunk_list(event_ids, MAX_EVENT_IDS_PER_VIEW_REQUEST)

    for batch_number, batch in enumerate(event_id_batches, start=1):
        print(f"Requesting event/view batch {batch_number}/{len(event_id_batches)}")

        params = {
            "token": token,
            "event_id": ",".join(batch),
        }

        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        detailed_events = data.get("results", [])

        all_detailed_events.extend(detailed_events)

    return all_detailed_events


def main():
    # Makes sure .env loads even if the IDE runs this from a weird folder
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")

    token = os.getenv("BETS_API_TOKEN")

    if not token:
        raise ValueError("BETS_API_TOKEN is missing. Check your .env file.")

    # Use yesterday as a simple historical test date
    day = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    print(f"Getting ended table tennis events for: {day}")

    ended_events = get_ended_events(token, day)

    print(f"Ended events found: {len(ended_events)}")

    if not ended_events:
        print("No ended events found. Try changing the date.")
        return

    event_ids = [event["id"] for event in ended_events]

    detailed_events = get_event_views(token, event_ids)

    print(f"Detailed events returned: {len(detailed_events)}")

    # Find the first event that actually has timeline data
    event_with_timeline = None

    for event in detailed_events:
        timeline = event.get("timeline", [])

        if timeline:
            event_with_timeline = event
            break

    if event_with_timeline is None:
        print("No event with timeline found.")
        return

    print("\nUsing this event as our one-match test:")
    print("Match ID:", event_with_timeline.get("id"))
    print("League:", event_with_timeline.get("league", {}).get("name"))
    print("Home:", event_with_timeline.get("home", {}).get("name"))
    print("Away:", event_with_timeline.get("away", {}).get("name"))
    print("Final match score:", event_with_timeline.get("ss"))

    print("\nSet scores:")
    pprint(event_with_timeline.get("scores"))

    print("\nTimeline length:", len(event_with_timeline.get("timeline", [])))

    rows = parse_event_to_score_state_rows(event_with_timeline)

    df = pd.DataFrame(rows)

    print("\nCleaned score-state DataFrame shape:")
    print(df.shape)

    print("\nFirst 10 cleaned rows:")
    print(df.head(10))

    print("\nLast 10 cleaned rows:")
    print(df.tail(10))

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nLeader won set counts:")
    print(df["leader_won_set"].value_counts(dropna=False))


if __name__ == "__main__":
    main()