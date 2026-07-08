from src.config.settings import (
    KEEP_ONLY_SETS_1_TO_5,
    TAB_LEAGUES,
)


def remove_invalid_match_sets(df, issues_df):
    if issues_df.empty:
        return df.copy()

    bad_match_sets = issues_df[["match_id", "set_number"]].drop_duplicates().copy()

    bad_match_sets["match_id"] = bad_match_sets["match_id"].astype(str)
    bad_match_sets["set_number"] = bad_match_sets["set_number"].astype(int)

    clean_df = df.copy()
    clean_df["match_id"] = clean_df["match_id"].astype(str)
    clean_df["set_number"] = clean_df["set_number"].astype(int)

    flagged_df = clean_df.merge(
        bad_match_sets.assign(is_bad_match_set=1),
        on=["match_id", "set_number"],
        how="left",
    )

    clean_df = flagged_df[flagged_df["is_bad_match_set"].isna()].copy()
    clean_df = clean_df.drop(columns=["is_bad_match_set"])

    return clean_df


def keep_sets_1_to_5(df):
    if not KEEP_ONLY_SETS_1_TO_5:
        return df.copy()

    return df[df["set_number"] <= 5].copy()


def create_tab_league_dataset(df):
    return df[df["league"].isin(TAB_LEAGUES)].copy()


def create_leader_dataset(df):
    leader_df = df[df["leader"] != "tie"].copy()
    leader_df = leader_df.dropna(subset=["leader_won_set"])

    leader_df["leader_won_set"] = leader_df["leader_won_set"].astype(int)

    leader_df["leader_score_state"] = (
        leader_df["leader_points"].astype(int).astype(str)
        + "-"
        + leader_df["trailer_points"].astype(int).astype(str)
    )

    return leader_df


def clean_daily_score_states(df, issues_df):
    valid_df = remove_invalid_match_sets(df, issues_df)
    valid_sets_df = keep_sets_1_to_5(valid_df)
    tab_df = create_tab_league_dataset(valid_sets_df)
    leader_tab_df = create_leader_dataset(tab_df)

    return {
        "all_valid": valid_sets_df,
        "tab": tab_df,
        "leader_tab": leader_tab_df,
    }