def create_baseline_probability_table(leader_df):
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