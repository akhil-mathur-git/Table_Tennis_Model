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



