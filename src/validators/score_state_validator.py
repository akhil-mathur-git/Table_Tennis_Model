import pandas as pd


VALIDATION_COLUMNS = [
    "match_id",
    "league",
    "set_number",
    "issue",
    "details",
]


def validate_set_group(group):
    issues = []

    group = group.sort_values("point_number_in_set")

    match_id = group["match_id"].iloc[0]
    league = group["league"].iloc[0]
    set_number = group["set_number"].iloc[0]

    final_home = int(group["set_final_home_points"].iloc[0])
    final_away = int(group["set_final_away_points"].iloc[0])

    last_home = int(group["home_points"].iloc[-1])
    last_away = int(group["away_points"].iloc[-1])

    expected_points = final_home + final_away
    actual_points = len(group)

    if last_home != final_home or last_away != final_away:
        issues.append({
            "match_id": match_id,
            "league": league,
            "set_number": set_number,
            "issue": "last_timeline_score_does_not_match_final_set_score",
            "details": f"last={last_home}-{last_away}, final={final_home}-{final_away}",
        })

    if actual_points != expected_points:
        issues.append({
            "match_id": match_id,
            "league": league,
            "set_number": set_number,
            "issue": "timeline_length_does_not_match_total_set_points",
            "details": f"actual_rows={actual_points}, expected_points={expected_points}",
        })

    expected_set_winner = "home" if final_home > final_away else "away"
    stored_set_winner = group["set_winner"].iloc[0]

    if stored_set_winner != expected_set_winner:
        issues.append({
            "match_id": match_id,
            "league": league,
            "set_number": set_number,
            "issue": "stored_set_winner_incorrect",
            "details": f"stored={stored_set_winner}, expected={expected_set_winner}",
        })

    previous_home = 0
    previous_away = 0

    for _, row in group.iterrows():
        current_home = int(row["home_points"])
        current_away = int(row["away_points"])
        point_winner = row["point_winner"]

        home_change = current_home - previous_home
        away_change = current_away - previous_away

        valid_score_progression = (
            (home_change == 1 and away_change == 0)
            or (home_change == 0 and away_change == 1)
        )

        if not valid_score_progression:
            issues.append({
                "match_id": match_id,
                "league": league,
                "set_number": set_number,
                "issue": "invalid_score_progression",
                "details": (
                    f"previous={previous_home}-{previous_away}, "
                    f"current={current_home}-{current_away}, "
                    f"home_change={home_change}, away_change={away_change}"
                ),
            })

        if home_change == 1 and away_change == 0:
            expected_point_winner = "home"
        elif home_change == 0 and away_change == 1:
            expected_point_winner = "away"
        else:
            expected_point_winner = None

        if expected_point_winner is not None and point_winner != expected_point_winner:
            issues.append({
                "match_id": match_id,
                "league": league,
                "set_number": set_number,
                "issue": "point_winner_does_not_match_score_change",
                "details": (
                    f"score={current_home}-{current_away}, "
                    f"stored={point_winner}, expected={expected_point_winner}"
                ),
            })

        previous_home = current_home
        previous_away = current_away

    return issues


def validate_score_states(df):
    all_issues = []

    if df.empty:
        return pd.DataFrame(columns=VALIDATION_COLUMNS)

    grouped = df.groupby(["match_id", "set_number"], sort=False)

    for _, group in grouped:
        issues = validate_set_group(group)
        all_issues.extend(issues)

    if not all_issues:
        return pd.DataFrame(columns=VALIDATION_COLUMNS)

    return pd.DataFrame(all_issues)