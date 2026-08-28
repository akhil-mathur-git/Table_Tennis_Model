import argparse

import pandas as pd

from archive.src.baselines.baseline_probability import create_baseline_probability_table
from archive.src.cleaners.score_state_cleaner import clean_daily_score_states
from archive.src.clients.betsapi_client import BetsAPIClient
from archive.src.config.settings import (
    CLEANED_DIR,
    COMBINED_DIR,
    DAILY_DIR,
    MAX_EVENT_IDS_PER_VIEW_REQUEST,
    RAW_ENDED_EVENTS_DIR,
    RAW_EVENT_VIEWS_DIR,
    VALIDATION_DIR,
    ensure_data_dirs,
)
from archive.src.parsers.score_state_parser import parse_events_to_dataframe
from archive.src.utils.dates import date_range
from archive.src.utils.io import load_json, save_dataframe, save_json
from archive.src.validators.score_state_validator import validate_score_states


def chunk_list(items, chunk_size):
    chunks = []

    for i in range(0, len(items), chunk_size):
        chunks.append(items[i:i + chunk_size])

    return chunks


def collect_ended_events_for_day(client, day, force_api=False, max_pages=None):
    all_events = []

    page = 1
    total_events = None

    while True:
        page_path = RAW_ENDED_EVENTS_DIR / day / f"page_{page}.json"

        if page_path.exists() and not force_api:
            print(f"Loading ended events from cache: {page_path}")
            data = load_json(page_path)
        else:
            print(f"Requesting ended events: day={day}, page={page}")
            data = client.get_ended_events_page(day=day, page=page)
            save_json(data, page_path)

        pager = data.get("pager", {})
        results = data.get("results", [])

        if total_events is None:
            total_events = int(pager.get("total", 0))
            per_page = int(pager.get("per_page", 50))

            estimated_pages = (total_events + per_page - 1) // per_page

            print(f"Total ended events available for {day}: {total_events}")
            print(f"Estimated pages: {estimated_pages}")

        if not results:
            print(f"No results on page {page}. Stopping ended-events collection.")
            break

        all_events.extend(results)

        print(f"Collected {len(all_events)} / {total_events} ended events for {day}")

        if max_pages is not None and page >= max_pages:
            print(f"Reached max_pages={max_pages}. Stopping early for test run.")
            break

        if total_events is not None and len(all_events) >= total_events:
            break

        page += 1

    return all_events


def collect_event_views_for_day(client, day, event_ids, force_api=False):
    all_detailed_events = []

    event_id_batches = chunk_list(event_ids, MAX_EVENT_IDS_PER_VIEW_REQUEST)

    print(f"Event/view batches needed for {day}: {len(event_id_batches)}")

    for batch_number, batch in enumerate(event_id_batches, start=1):
        batch_path = RAW_EVENT_VIEWS_DIR / day / f"batch_{batch_number:03d}.json"

        if batch_path.exists() and not force_api:
            print(f"Loading event/view from cache: batch {batch_number}/{len(event_id_batches)}")
            data = load_json(batch_path)
        else:
            print(f"Requesting event/view batch {batch_number}/{len(event_id_batches)}")
            data = client.get_event_views(batch)
            save_json(data, batch_path)

        detailed_events = data.get("results", [])
        all_detailed_events.extend(detailed_events)

    return all_detailed_events


def process_day(client, day, force_api=False, max_pages=None):
    print("\n" + "=" * 80)
    print(f"Processing day: {day}")
    print("=" * 80)

    ended_events = collect_ended_events_for_day(
        client=client,
        day=day,
        force_api=force_api,
        max_pages=max_pages,
    )

    print(f"\nTotal ended events collected for {day}: {len(ended_events)}")

    if not ended_events:
        print(f"No ended events found for {day}. Skipping.")
        return

    event_ids = [event["id"] for event in ended_events]

    detailed_events = collect_event_views_for_day(
        client=client,
        day=day,
        event_ids=event_ids,
        force_api=force_api,
    )

    print(f"\nDetailed events returned for {day}: {len(detailed_events)}")

    score_states_df, parse_summary = parse_events_to_dataframe(detailed_events)

    print("\nParse summary:")
    for key, value in parse_summary.items():
        print(f"{key}: {value}")

    daily_path = DAILY_DIR / f"score_states_full_day_{day}.csv"
    save_dataframe(score_states_df, daily_path)

    print("\nSaved daily score-state data to:")
    print(daily_path)

    issues_df = validate_score_states(score_states_df)

    validation_path = VALIDATION_DIR / f"validation_issues_{day}.csv"
    save_dataframe(issues_df, validation_path)

    print("\nValidation issue count:", len(issues_df))
    print("Saved validation issues to:")
    print(validation_path)

    cleaned_datasets = clean_daily_score_states(score_states_df, issues_df)

    all_valid_df = cleaned_datasets["all_valid"]
    tab_df = cleaned_datasets["tab"]
    leader_tab_df = cleaned_datasets["leader_tab"]

    baseline_df = create_baseline_probability_table(leader_tab_df)

    all_valid_path = CLEANED_DIR / f"clean_score_states_all_valid_{day}.csv"
    tab_path = CLEANED_DIR / f"clean_score_states_tab_leagues_{day}.csv"
    leader_tab_path = CLEANED_DIR / f"leader_score_states_tab_leagues_{day}.csv"
    baseline_path = CLEANED_DIR / f"baseline_probabilities_tab_leagues_{day}.csv"

    save_dataframe(all_valid_df, all_valid_path)
    save_dataframe(tab_df, tab_path)
    save_dataframe(leader_tab_df, leader_tab_path)
    save_dataframe(baseline_df, baseline_path)

    print("\nCleaned daily outputs:")
    print("All valid rows:", len(all_valid_df))
    print("TAB rows:", len(tab_df))
    print("Leader TAB rows:", len(leader_tab_df))
    print("Baseline rows:", len(baseline_df))

    print("\nSaved cleaned outputs to:")
    print(all_valid_path)
    print(tab_path)
    print(leader_tab_path)
    print(baseline_path)


def combine_outputs(days, start_date, end_date):
    print("\n" + "=" * 80)
    print("Combining cleaned daily outputs")
    print("=" * 80)

    tab_dfs = []
    leader_dfs = []

    for day in days:
        tab_path = CLEANED_DIR / f"clean_score_states_tab_leagues_{day}.csv"
        leader_path = CLEANED_DIR / f"leader_score_states_tab_leagues_{day}.csv"

        if tab_path.exists():
            tab_dfs.append(pd.read_csv(tab_path, dtype={"match_id": str}))

        if leader_path.exists():
            leader_dfs.append(pd.read_csv(leader_path, dtype={"match_id": str}))

    if not tab_dfs or not leader_dfs:
        print("No cleaned daily files found to combine.")
        return

    combined_tab_df = pd.concat(tab_dfs, ignore_index=True)
    combined_leader_df = pd.concat(leader_dfs, ignore_index=True)

    combined_baseline_df = create_baseline_probability_table(combined_leader_df)

    label = f"{start_date}_to_{end_date}"

    combined_tab_path = COMBINED_DIR / f"clean_score_states_tab_leagues_{label}.csv"
    combined_leader_path = COMBINED_DIR / f"leader_score_states_tab_leagues_{label}.csv"
    combined_baseline_path = COMBINED_DIR / f"baseline_probabilities_tab_leagues_{label}.csv"

    save_dataframe(combined_tab_df, combined_tab_path)
    save_dataframe(combined_leader_df, combined_leader_path)
    save_dataframe(combined_baseline_df, combined_baseline_path)

    print("\nCombined TAB dataset:")
    print("Rows:", len(combined_tab_df))
    print("Unique matches:", combined_tab_df["match_id"].nunique())

    print("\nCombined leader dataset:")
    print("Rows:", len(combined_leader_df))
    print("Unique matches:", combined_leader_df["match_id"].nunique())

    print("\nCombined baseline probability preview:")
    print(combined_baseline_df.head(20))

    print("\nSaved combined outputs to:")
    print(combined_tab_path)
    print(combined_leader_path)
    print(combined_baseline_path)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--start-date", required=True, help="Start date in YYYYMMDD format")
    parser.add_argument("--end-date", required=True, help="End date in YYYYMMDD format")
    parser.add_argument("--force-api", action="store_true", help="Ignore cached raw files and call API again")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional limit for testing")

    args = parser.parse_args()

    ensure_data_dirs()

    client = BetsAPIClient()

    days = list(date_range(args.start_date, args.end_date))

    print("Pipeline dates:")
    print(days)

    for day in days:
        process_day(
            client=client,
            day=day,
            force_api=args.force_api,
            max_pages=args.max_pages,
        )

    combine_outputs(days, args.start_date, args.end_date)

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()