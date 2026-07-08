from pathlib import Path

import pandas as pd


TAB_LEAGUES = [
    "TT Cup",
    "TT Elite Series",
    "Czech Liga Pro",
]

KEEP_ONLY_SETS_1_TO_5 = True


def find_latest_full_day_file(project_root):
    """
    Finds the newest full-day score-state CSV.

    Example:
    data/processed/score_states_full_day_20260607.csv
    """
    processed_dir = project_root / "data" / "processed"
    files = sorted(processed_dir.glob("score_states_full_day_*.csv"))

    if not files:
        raise FileNotFoundError(
            "No score_states_full_day_*.csv files found in data/processed."
        )

    return files[-1]


def get_day_from_filename(csv_path):
    """
    Example:
    score_states_full_day_20260607.csv -> 20260607
    """
    return csv_path.stem.replace("score_states_full_day_", "")


def load_score_states(csv_path):
    """
    Loads the processed score-state data.

    IDs are loaded as strings because they are identifiers, not numbers.
    """
    dtype_map = {
        "match_id": str,
        "sport_id": str,
        "league_id": str,
        "home_player_id": str,
        "away_player_id": str,
        "timeline_id": str,
    }

    return pd.read_csv(csv_path, dtype=dtype_map)


def remove_invalid_match_sets(df, validation_issues_path):
    """
    Removes match-set groups that failed validation.

    If match 123, set 2 has an issue, remove all rows where:
    match_id = 123 and set_number = 2

    We remove match-sets, not individual rows, because a broken timeline affects
    the whole set sequence.
    """
    if not validation_issues_path.exists():
        print("\nNo validation_issues.csv found. Skipping validation-based filtering.")
        return df

    issues_df = pd.read_csv(validation_issues_path)

    if issues_df.empty:
        print("\nvalidation_issues.csv is empty. No invalid match-sets removed.")
        return df

    issues_df["match_id"] = issues_df["match_id"].astype(str)
    issues_df["set_number"] = issues_df["set_number"].astype(int)

    bad_match_sets = issues_df[["match_id", "set_number"]].drop_duplicates()

    print("\nInvalid match-sets to remove:", len(bad_match_sets))

    df = df.copy()
    df["match_id"] = df["match_id"].astype(str)
    df["set_number"] = df["set_number"].astype(int)

    df_with_flags = df.merge(
        bad_match_sets.assign(is_bad_match_set=1),
        on=["match_id", "set_number"],
        how="left",
    )

    clean_df = df_with_flags[df_with_flags["is_bad_match_set"].isna()].copy()
    clean_df = clean_df.drop(columns=["is_bad_match_set"])

    return clean_df


def keep_sets_1_to_5(df):
    """
    Keeps normal best-of-5 style set numbers.

    We are NOT removing scores above 11.
    Scores like 12-10 or 15-13 are valid table tennis deuce scores.
    """
    if not KEEP_ONLY_SETS_1_TO_5:
        return df

    return df[df["set_number"] <= 5].copy()


def create_tab_league_dataset(df):
    """
    Keeps only leagues that are relevant for TAB NZ betting.
    """
    return df[df["league"].isin(TAB_LEAGUES)].copy()


def create_leader_dataset(df):
    """
    Creates the leader-perspective dataset.

    This is for questions like:
    At 7-5, how often does the leader win the set?

    Tied scores are removed because there is no leader at 5-5, 8-8, etc.
    """
    leader_df = df[df["leader"] != "tie"].copy()

    leader_df = leader_df.dropna(subset=["leader_won_set"])

    leader_df["leader_won_set"] = leader_df["leader_won_set"].astype(int)

    leader_df["leader_score_state"] = (
        leader_df["leader_points"].astype(int).astype(str)
        + "-"
        + leader_df["trailer_points"].astype(int).astype(str)
    )

    return leader_df


def create_baseline_probability_table(leader_df):
    """
    Creates empirical probabilities:

    P(leader wins set | leader score, trailer score)

    Example:
    At 7-5, leader wins 72% of the time.
    """
    baseline_df = (
        leader_df
        .groupby(["leader_points", "trailer_points", "leader_score_state"])
        .agg(
            examples=("leader_won_set", "size"),
            leader_wins=("leader_won_set", "sum"),
            leader_win_probability=("leader_won_set", "mean"),
        )
        .reset_index()
    )

    baseline_df["leader_win_probability"] = baseline_df[
        "leader_win_probability"
    ].round(4)

    baseline_df = baseline_df.sort_values(
        ["leader_points", "trailer_points"],
        ascending=[True, True],
    )

    return baseline_df


def print_summary(name, df):
    print(f"\n{name}")
    print("-" * len(name))
    print("Rows:", len(df))
    print("Unique matches:", df["match_id"].nunique())

    if "league" in df.columns:
        print("\nRows by league:")
        print(df["league"].value_counts())

    if "set_number" in df.columns:
        print("\nRows by set number:")
        print(df["set_number"].value_counts().sort_index())


def main():
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    project_root = Path(__file__).resolve().parents[1]
    processed_dir = project_root / "data" / "processed"

    full_day_path = find_latest_full_day_file(project_root)
    validation_issues_path = processed_dir / "validation_issues.csv"

    day = get_day_from_filename(full_day_path)

    print("Loading full-day dataset:")
    print(full_day_path)

    df = load_score_states(full_day_path)

    print_summary("Original full-day dataset", df)

    # Step 1: remove invalid match-set groups found by validation
    valid_df = remove_invalid_match_sets(df, validation_issues_path)

    print_summary("After removing invalid match-sets", valid_df)

    # Step 2: keep only sets 1 to 5 for the first model
    # This does NOT remove scores above 11.
    valid_sets_df = keep_sets_1_to_5(valid_df)

    print_summary("After keeping set numbers 1 to 5", valid_sets_df)

    # Step 3: create TAB-focused modelling dataset
    tab_df = create_tab_league_dataset(valid_sets_df)

    print_summary("TAB-league score-state dataset", tab_df)

    # Step 4: create leader-perspective version
    leader_tab_df = create_leader_dataset(tab_df)

    print_summary("TAB-league leader-perspective dataset", leader_tab_df)

    print("\nLeader won set counts:")
    print(leader_tab_df["leader_won_set"].value_counts())

    # Step 5: create first baseline probability table
    baseline_tab_df = create_baseline_probability_table(leader_tab_df)

    print("\nBaseline probability table preview:")
    print(baseline_tab_df.head(20))

    print("\nBaseline probabilities for common score states:")
    common_states = [
        "1-0",
        "2-0",
        "3-1",
        "5-3",
        "7-5",
        "8-6",
        "10-8",
        "10-9",
        "11-10",
        "12-11",
    ]

    common_state_df = baseline_tab_df[
        baseline_tab_df["leader_score_state"].isin(common_states)
    ]

    print(common_state_df)

    # Step 6: save outputs
    all_valid_output_path = processed_dir / f"clean_score_states_all_valid_{day}.csv"
    tab_output_path = processed_dir / f"clean_score_states_tab_leagues_{day}.csv"
    leader_tab_output_path = processed_dir / f"leader_score_states_tab_leagues_{day}.csv"
    baseline_tab_output_path = processed_dir / f"baseline_probabilities_tab_leagues_{day}.csv"

    valid_sets_df.to_csv(all_valid_output_path, index=False)
    tab_df.to_csv(tab_output_path, index=False)
    leader_tab_df.to_csv(leader_tab_output_path, index=False)
    baseline_tab_df.to_csv(baseline_tab_output_path, index=False)

    print("\nSaved all-valid cleaned dataset to:")
    print(all_valid_output_path)

    print("\nSaved TAB-league cleaned dataset to:")
    print(tab_output_path)

    print("\nSaved TAB-league leader-perspective dataset to:")
    print(leader_tab_output_path)

    print("\nSaved TAB-league baseline probability table to:")
    print(baseline_tab_output_path)

    print("\nDone.")


if __name__ == "__main__":
    main()