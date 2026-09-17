import numpy as np
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta

#Get the parent folder
PROJECT_ROOT = Path(__file__).resolve().parents[1]

def build_feature_matrix(start_date,end_date):
    #List of dates
    dates = get_date_strings(start_date,end_date)
    #File paths of json files list
    paths = get_event_views(dates)
    #Get list of match dictionaries
    matches = get_matches_from_files(paths)
    #Clean data and only keep from TAB leagues
    clean_matches = remove_incomplete_data(matches)





def get_date_strings(start_date,end_date):
    """
    Inputs the start date and end date and outputs a LIST of all dates between them inclusive
    """
    current_date = datetime.strptime(start_date,"%Y%m%d")
    last_date = datetime.strptime(end_date, "%Y%m%d")
    dates = []
    while current_date <=last_date:
        date = datetime.strftime(current_date, "%Y%m%d")
        dates.append(date)
        current_date = current_date + timedelta(days = 1)
    return dates

def get_event_views(dates):
    """
    Inputs the list of dates and outputs a LIST of file paths
    """
    paths = []
    for date in dates:
        folder_path = (PROJECT_ROOT/"data"/"raw"/"betsapi"/"event_views"/date)
        json_files = sorted(folder_path.glob("*.json"))
        for json_file in json_files:
            paths.append(json_file)

    return paths

def get_matches_from_files(file_paths):
    """
    Inputs the LIST of file paths and outputs a long list of all the matches from the file paths
    """
    matches = []
    for file in file_paths:
        with open(file,"r",encoding = "utf-8") as f:
            data = json.load(f)
        temp_matches = data["results"]
        matches = matches + temp_matches
    return matches

def remove_incomplete_data(matches):
    """
    Inputs a full list of matches and outputs a list of matches with incomplete data removed.
    Also removes matches from leagues we are not using for the first TAB-focused version.
    """
    clean_matches = []

    ALLOWED_LEAGUE_IDS = {
        "29128",  # TT Elite Series
        "29097",  # TT Cup
        "22742",  # Czech Liga Pro
    }

    for match in matches:
        # Match ID
        if not match.get("id"):
            continue

        # League info
        league = match.get("league")
        if not league:
            continue

        league_id = league.get("id")
        if not league_id:
            continue

        if league_id not in ALLOWED_LEAGUE_IDS:
            continue

        # Home player info
        home = match.get("home")
        if not home:
            continue

        if not home.get("id"):
            continue

        if not home.get("name"):
            continue

        # Away player info
        away = match.get("away")
        if not away:
            continue

        if not away.get("id"):
            continue

        if not away.get("name"):
            continue

        # Final set scores
        scores = match.get("scores")
        if not scores:
            continue

        # Point-by-point timeline
        timeline = match.get("timeline")
        if not timeline:
            continue

        clean_matches.append(match)

    return clean_matches

def parse_score(score_string):
    """
    Inputs a score string like '7-5' and returns home_points and away_points as integers.
    """
    parts = score_string.split("-")
    home_points = int(parts[0])
    away_points = int(parts[1])
    return home_points, away_points

def get_home_won_set(scores, set_number):
    """
    Inputs the scores dict and set number and finds if home won that set
    """
    home = scores[str(set_number)]["home"]
    away = scores[str(set_number)]["away"]
    home = int(home)
    away = int(away)
    if home==away:
        return -1
    if home>away:
        return 1
    else:
        return 0

def get_sets_won_so_far(scores, set_number):
    """
    Inputs the final set scores dictionary and the current set number.
    Outputs how many sets home and away had won before the current set.
    """
    home_sets_won_so_far = 0
    away_sets_won_so_far = 0

    for previous_set_number in range(1, set_number):
        home_won_set = get_home_won_set(scores, previous_set_number)

        if home_won_set == -1:
            return -1, -1

        if home_won_set == 1:
            home_sets_won_so_far += 1
        else:
            away_sets_won_so_far += 1

    return home_sets_won_so_far, away_sets_won_so_far

def check_terminal_score_state(scores, home_points, away_points, set_number):
    """
    inputs the scores dictionary from the match and checks to see if the current score state is terminal
    """
    set_number = str(set_number)
    terminal_away = int(scores[set_number]["away"])
    terminal_home = int(scores[set_number]["home"])
    if terminal_away==away_points and terminal_home==home_points:
        return True
    else:
        return False



def build_rows(match):
    match_id = match["id"]
    league_name = match["league"]["name"]
    timeline = match["timeline"]
    rows = []
    for rep in timeline:

        row = {"match_id":match_id, "league": league_name}
        set_number = int(rep["gm"])
        row["set_number"] = set_number
        set_score = rep["ss"]
        home_points, away_points = parse_score(set_score)
        row["home_points"] = home_points
        row["away_points"] = away_points
        #Check if terminal score state
        if check_terminal_score_state(match["scores"],home_points,away_points,set_number):
            continue
        row["point_difference"] = home_points-away_points
        row["total_points_played"] = home_points + away_points
        home_sets_won_so_far, away_sets_won_so_far = get_sets_won_so_far(match["scores"], set_number)
        if home_sets_won_so_far == -1 or away_sets_won_so_far == -1:
            continue
        row["home_sets_won_so_far"] = home_sets_won_so_far
        row["away_sets_won_so_far"] = away_sets_won_so_far
        home_won_set = get_home_won_set(match["scores"],set_number)
        if home_won_set == -1:
            continue
        row["home_won_set"] = home_won_set
        rows.append(row)

    return rows