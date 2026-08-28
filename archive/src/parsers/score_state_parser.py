import pandas as pd


def parse_score(score_string):
    home_score, away_score = score_string.split("-")
    return int(home_score), int(away_score)


def point_winner_from_te(te_value):
    if te_value == "0":
        return "home"
    elif te_value == "1":
        return "away"
    return None


def get_set_final_score(event, set_number):
    scores = event.get("scores", {})
    set_score = scores.get(str(set_number))

    if set_score is None:
        return None, None

    return int(set_score["home"]), int(set_score["away"])


def get_set_winner(event, set_number):
    home_final, away_final = get_set_final_score(event, set_number)

    if home_final is None or away_final is None:
        return None

    if home_final > away_final:
        return "home"
    return "away"


def get_match_winner(event):
    final_match_score = event.get("ss")

    if final_match_score is None:
        return None

    home_sets, away_sets = parse_score(final_match_score)

    if home_sets > away_sets:
        return "home"
    return "away"


def parse_event_to_score_state_rows(event):
    rows = []

    match_id = event.get("id")
    sport_id = event.get("sport_id")
    match_time = event.get("time")
    time_status = event.get("time_status")

    league_id = event.get("league", {}).get("id")
    league_name = event.get("league", {}).get("name")

    home_player_id = event.get("home", {}).get("id")
    home_player = event.get("home", {}).get("name")

    away_player_id = event.get("away", {}).get("id")
    away_player = event.get("away", {}).get("name")

    final_match_score = event.get("ss")
    match_winner = get_match_winner(event)

    timeline = event.get("timeline", [])

    set_point_counts = {}

    for point_number_in_match, timeline_entry in enumerate(timeline, start=1):
        set_number_raw = timeline_entry.get("gm")
        score_state = timeline_entry.get("ss")
        te_value = timeline_entry.get("te")
        timeline_id = timeline_entry.get("id")

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
            "time_status": time_status,

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
            "timeline_id": timeline_id,

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


def parse_events_to_dataframe(detailed_events):
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

    df = pd.DataFrame(all_rows)

    summary = {
        "matches_checked": len(detailed_events),
        "matches_with_timeline": matches_with_timeline,
        "matches_without_timeline": matches_without_timeline,
        "matches_parsed_successfully": matches_parsed_successfully,
        "score_state_rows_created": len(all_rows),
    }

    return df, summary