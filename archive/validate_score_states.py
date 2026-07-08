from pathlib import Path

import pandas as pd


def find_latest_score_states_file(project_root):
    """
    Finds the newest processed full-day score-state CSV.

    Example file:
    data/processed/score_states_full_day_20260607.csv
    """
    processed_dir = project_root / "data" / "processed"

    files = sorted(processed_dir.glob("score_states_full_day_*.csv"))

    if not files:
        raise FileNotFoundError(
            "No score_states_full_day_*.csv files found in data/processed."
        )

    return files[-1]


def validate_set_group(group):
    """
    Validates one match-set group.

    One group = all point rows for one set in one match.
    """
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

    # Check 1: final timeline score should match official final set score
    if last_home != final_home or last_away != final_away:
        issues.append({
            "match_id": match_id,
            "league": league,
            "set_number": set_number,
            "issue": "last_timeline_score_does_not_match_final_set_score",
            "details": f"last={last_home}-{last_away}, final={final_home}-{final_away}",
        })

    # Check 2: number of rows should equal total points in the set
    if actual_points != expected_points:
        issues.append({
            "match_id": match_id,
            "league": league,
            "set_number": set_number,
            "issue": "timeline_length_does_not_match_total_set_points",
            "details": f"actual_rows={actual_points}, expected_points={expected_points}",
        })

    # Check 3: set winner should match final set score
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

    # Check 4: point progression should increase by exactly one point each row
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

        # Check 5: point_winner should match the score increase
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


def main():
    project_root = Path(__file__).resolve().parents[1]

    csv_path = find_latest_score_states_file(project_root)

    print("Validating file:")
    print(csv_path)

    df = pd.read_csv(csv_path)

    print("\nDataset shape:")
    print(df.shape)

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nBasic dataset summary:")
    print("Rows:", len(df))
    print("Unique matches:", df["match_id"].nunique())
    print("Unique leagues:", df["league"].nunique())
    print("Unique players:", pd.concat([df["home_player"], df["away_player"]]).nunique())

    print("\nRows by league:")
    print(df["league"].value_counts())

    print("\nRows by set number:")
    print(df["set_number"].value_counts().sort_index())

    print("\nMatches by set number max:")
    max_set_by_match = df.groupby("match_id")["set_number"].max()
    print(max_set_by_match.value_counts().sort_index())

    print("\nLeader won set counts:")
    print(df["leader_won_set"].value_counts(dropna=False))

    # Duplicate checks
    print("\nDuplicate checks:")

    duplicate_point_rows = df.duplicated(
        subset=["match_id", "set_number", "point_number_in_set"]
    ).sum()

    print("Duplicate match/set/point_number rows:", duplicate_point_rows)

    if "timeline_id" in df.columns:
        duplicate_timeline_ids = df["timeline_id"].duplicated().sum()
        print("Duplicate timeline IDs:", duplicate_timeline_ids)

    # Missing value checks
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
        "set_final_home_points",
        "set_final_away_points",
    ]

    print("\nMissing values in important columns:")
    print(df[important_columns].isna().sum())

    # Weird score checks
    print("\nScore range checks:")
    print("Minimum home_points:", df["home_points"].min())
    print("Maximum home_points:", df["home_points"].max())
    print("Minimum away_points:", df["away_points"].min())
    print("Maximum away_points:", df["away_points"].max())

    scores_over_11 = df[(df["home_points"] > 11) | (df["away_points"] > 11)]

    print("Rows where either player has more than 11 points:", len(scores_over_11))

    if len(scores_over_11) > 0:
        print("\nExample rows with scores over 11:")
        print(
            scores_over_11[
                [
                    "match_id",
                    "league",
                    "set_number",
                    "score_state",
                    "home_points",
                    "away_points",
                    "set_final_home_points",
                    "set_final_away_points",
                ]
            ].head(10)
        )

    # Validate every match-set group
    print("\nValidating each match-set score progression...")

    all_issues = []

    grouped = df.groupby(["match_id", "set_number"], sort=False)

    for _, group in grouped:
        issues = validate_set_group(group)
        all_issues.extend(issues)

    print("\nValidation issue count:", len(all_issues))

    if all_issues:
        issues_df = pd.DataFrame(all_issues)

        print("\nIssue counts by type:")
        print(issues_df["issue"].value_counts())

        print("\nFirst 20 validation issues:")
        print(issues_df.head(20))

        output_dir = project_root / "data" / "processed"
        output_path = output_dir / "validation_issues.csv"

        issues_df.to_csv(output_path, index=False)

        print("\nSaved validation issues to:")
        print(output_path)

    else:
        print("\nNo validation issues found. Dataset looks internally consistent.")

    print("\nValidation complete.")


if __name__ == "__main__":
    main()