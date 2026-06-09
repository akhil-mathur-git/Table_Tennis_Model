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


def point_winner_from_te(te_value):
    """
    In BetsAPI table tennis timeline:
    te = '0' means home scored the point
    te = '1' means away scored the point
    """
    if te_value == "0":
        return "home"
    elif te_value == "1":
        return "away"
    else:
        return None


def get_set_final_score(event, set_number):
    """
    Gets the final score for a particular set.

    Example:
    scores = {
        '1': {'home': '11', 'away': '7'}
    }

    returns:
    11, 7
    """
    scores = event.get("scores", {})
    set_score = scores.get(str(set_number))

    if set_score is None:
        return None, None

    home_final_points = int(set_score["home"])
    away_final_points = int(set_score["away"])

    return home_final_points, away_final_points


def get_set_winner(event, set_number):
    """
    Uses the final set score to determine who won the set.
    """
    home_final_points, away_final_points = get_set_final_score(event, set_number)

    if home_final_points is None or away_final_points is None:
        return None

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


def parse_event_to_score_state_rows(event):
    """
    Converts one BetsAPI table tennis event into clean score-state rows.

    One row = one score state after a point is played.
    """
    rows = []

    match_id = event.get("id")
    sport_id = event.get("sport_id")
    match_time = event.get("time")
    league_id = event.get("league", {}).get("id")
    league_name = event.get("league", {}).get("name")

    home_player_id = event.get("home", {}).get("id")
    home_player = event.get("home", {}).get("name")
    away_player_id = event.get("away", {}).get("id")
    away_player = event.get("away", {}).get("name")

    final_match_score = event.get("ss")
    match_winner = get_match_winner(event)

    timeline = event.get("timeline", [])

    # This tracks point number inside each set.
    # Example:
    # set_point_counts[1] = how many points we have seen in set 1 so far
    set_point_counts = {}

    for point_number_in_match, timeline_entry in enumerate(timeline, start=1):
        set_number_raw = timeline_entry.get("gm")
        score_state = timeline_entry.get("ss")
        te_value = timeline_entry.get("te")

        if set_number_raw is None or score_state is None:
            continue

        set_number = int(set_number_raw)

        if set_number not in set_point_counts:
            set_point_counts[set_number] = 0

        set_point_counts[set_number] += 1
        point_number_in_set = set_point_counts[set_number]

        home_points, away_points = parse_score(score_state)

        point_winner = point_winner_from_te(te_value)

        set_winner = get_set_winner(event, set_number)
        set_final_home_points, set_final_away_points = get_set_final_score(event, set_number)

        if set_winner is None:
            continue

        home_won_set = 1 if set_winner == "home" else 0
        away_won_set = 1 if set_winner == "away" else 0

        home_won_match = 1 if match_winner == "home" else 0
        away_won_match = 1 if match_winner == "away" else 0

        point_difference = home_points - away_points
        absolute_point_difference = abs(point_difference)
        total_points_played = home_points + away_points

        if home_points > away_points:
            leader = "home"
            trailer = "away"
            leader_points = home_points
            trailer_points = away_points
            leader_won_set = 1 if set_winner == "home" else 0

        elif away_points > home_points:
            leader = "away"
            trailer = "home"
            leader_points = away_points
            trailer_points = home_points
            leader_won_set = 1 if set_winner == "away" else 0

        else:
            leader = "tie"
            trailer = "tie"
            leader_points = home_points
            trailer_points = away_points
            leader_won_set = None

        row = {
            "match_id": match_id,
            "sport_id": sport_id,
            "match_time": match_time,

            "league_id": league_id,
            "league": league_name,

            "home_player_id": home_player_id,
            "home_player": home_player,
            "away_player_id": away_player_id,
            "away_player": away_player,

            "final_match_score": final_match_score,
            "match_winner": match_winner,

            "set_number": set_number,
            "point_number_in_match": point_number_in_match,
            "point_number_in_set": point_number_in_set,

            "score_state": score_state,
            "home_points": home_points,
            "away_points": away_points,
            "point_winner": point_winner,

            "set_final_home_points": set_final_home_points,
            "set_final_away_points": set_final_away_points,
            "set_winner": set_winner,

            "home_won_set": home_won_set,
            "away_won_set": away_won_set,
            "home_won_match": home_won_match,
            "away_won_match": away_won_match,

            "point_difference": point_difference,
            "absolute_point_difference": absolute_point_difference,
            "total_points_played": total_points_played,

            "leader": leader,
            "trailer": trailer,
            "leader_points": leader_points,
            "trailer_points": trailer_points,
            "leader_won_set": leader_won_set,
        }

        rows.append(row)

    return rows


def get_ended_events(token, day):
    """
    Gets completed table tennis matches for one date.

    For now, this gets the first page of ended events.
    Later we can add pagination if needed.
    """
    url = "https://api.b365api.com/v3/events/ended"

    params = {
        "token": token,
        "sport_id": SPORT_ID_TABLE_TENNIS,
        "day": day,
    }

    response = requests.get(url, params=params, timeout=20)

    print("Ended events status code:", response.status_code)

    response.raise_for_status()

    data = response.json()

    print("\nEnded events pager info:")
    pprint(data.get("pager"))

    return data.get("results", [])


def get_event_views(token, event_ids):
    """
    Gets detailed event data for a list of event IDs.

    BetsAPI allows multiple event IDs in one request.
    We request them in batches of 10 to keep request count low.
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
    # Makes sure .env loads properly even if the IDE runs from a weird folder
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")

    token = os.getenv("BETS_API_TOKEN")

    if not token:
        raise ValueError("BETS_API_TOKEN is missing. Check your .env file.")

    # Use yesterday as a first one-day test
    day = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    print(f"Collecting one day of table tennis data for: {day}\n")

    ended_events = get_ended_events(token, day)

    print(f"\nEnded events found: {len(ended_events)}")

    if not ended_events:
        print("No ended events found. Try changing the date.")
        return

    event_ids = [event["id"] for event in ended_events]

    print(f"Event IDs collected: {len(event_ids)}")

    detailed_events = get_event_views(token, event_ids)

    print(f"\nDetailed events returned: {len(detailed_events)}")

    all_rows = []

    matches_with_timeline = 0
    matches_without_timeline = 0
    matches_parsed_successfully = 0

    for event in detailed_events:
        timeline = event.get("timeline", [])

        if not timeline:
            matches_without_timeline += 1
            continue

        matches_with_timeline += 1

        rows = parse_event_to_score_state_rows(event)

        if rows:
            matches_parsed_successfully += 1
            all_rows.extend(rows)

    print("\nParsing summary:")
    print("Matches checked:", len(detailed_events))
    print("Matches with timeline:", matches_with_timeline)
    print("Matches without timeline:", matches_without_timeline)
    print("Matches parsed successfully:", matches_parsed_successfully)
    print("Total score-state rows created:", len(all_rows))

    if not all_rows:
        print("\nNo rows were created. Something went wrong or no timelines were available.")
        return

    df = pd.DataFrame(all_rows)

    print("\nCleaned one-day DataFrame shape:")
    print(df.shape)

    important_columns = [
        "match_id",
        "league",
        "home_player",
        "away_player",
        "set_number",
        "point_number_in_set",
        "score_state",
        "home_points",
        "away_points",
        "point_winner",
        "set_winner",
        "home_won_set",
        "leader",
        "leader_points",
        "trailer_points",
        "leader_won_set",
    ]

    print("\nFirst 10 cleaned rows:")
    print(df[important_columns].head(10))

    print("\nLast 10 cleaned rows:")
    print(df[important_columns].tail(10))

    print("\nRows by league:")
    print(df["league"].value_counts())

    print("\nRows by set number:")
    print(df["set_number"].value_counts().sort_index())

    print("\nLeader won set counts:")
    print(df["leader_won_set"].value_counts(dropna=False))

    # Save processed CSV
    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"score_states_{day}.csv"

    df.to_csv(output_path, index=False)

    print(f"\nSaved processed score-state data to:")
    print(output_path)


if __name__ == "__main__":
    main()