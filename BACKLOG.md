# Table Tennis ML Project Backlog

This file contains feature ideas and modelling improvements to revisit after the first version of the feature matrix and baseline model are working.

---

## Version 1 Feature Matrix

First implementation should stay simple and clean.

### Target label

- `home_won_set`
  - `1` if the home player eventually wins the current set.
  - `0` if the away player eventually wins the current set.

### Features

- `home_points`
- `away_points`
- `point_difference`
  - `home_points - away_points`
- `total_points_played`
  - `home_points + away_points`
- `set_number`
- `home_sets_won_so_far`
- `away_sets_won_so_far`

### Not included in Version 1

- `is_home_leading`
- `is_away_leading`
- `is_tied`
- Serving information
- Momentum information
- Player information
- Previous set scores

Reason: keep the first model minimal and avoid redundant/noisy features until the base pipeline works.

---

## Features to revisit later

### Serving information

- Check if there is any way to get who serves first.
- If first-server data is not available, test whether home/away serving first can be inferred.
- Possible inferred feature:
  - `current_server`
  - `home_serving`
  - `away_serving`
- Only add this if we can measure it reliably.
- Do not assume home serves first without evidence.

---

### Momentum information

Potential features:

- Who won the last point.
- Who won the last 3 points.
- Current point streak.
- Number of recent points won by home.
- Number of recent points won by away.

#### Full point sequence so far

Represent the full point-by-point path up to the current score state.

Example:

If the current set score is 2-1 to home, the point sequence could be:

```text
101
```

where:

```text
1 = home won the point
0 = away won the point
```

This captures the entire path of the set up to that point, not just the current score.

Caution:

- This could be high-cardinality.
- It may overfit if used badly.
- Test whether it improves out-of-sample log loss/calibration before keeping it.

---

### Previous set score information

Include the scores of sets completed before the current set.

Example:

Before set 3, the model could know:

```text
Set 1: 11-9
Set 2: 8-11
```

Potential ideas:

- Previous set winner.
- Previous set score margin.
- Whether previous set was a close loss.
- Whether previous set was a close win.
- Whether previous set was a dominant loss.
- Whether previous set was a dominant win.

Reason:

- Prior close losses/wins or dominant set outcomes may affect player mentality and future set performance.

Important:

- Only use sets completed before the current row/set.
- Never use future set scores.

---

### Player information

Potential features:

- Elo rating.
- Historical record.
- Recent form.
- Head-to-head record.
- Clutch/choke factors.
- Player strength difference.
- Recent win rate.
- Recent set win rate.

Important:

- Player features must only use matches before the current match.
- Do not calculate player stats using the full dataset, because that would leak future information.

---

## Player mentality / response-to-state features

Long-term idea: the model should not only learn the general probability of a score state, but how specific players respond to that state.

The aim is to model things like:

```text
At this score state, with this player, after this previous set result, under this match pressure, what happens?
```

Potential features:

- Closing factor when a player is leading late in a set.
- Comeback factor when a player is trailing late in a set.
- Late-set pressure factor.
- Deciding-set performance.
- Response after losing the previous set.
- Response after winning the previous set.
- Effect of previous set score margin:
  - close loss
  - close win
  - dominant loss
  - dominant win
- Interaction between current score state and player-specific behaviour.

Preferred approach:

- First build a base score-state model.
- Then calculate player-specific pressure features using:

```text
actual outcome - expected outcome
```

Example:

If the base model says a player should win from a certain state 80% of the time, but a specific player historically wins from that type of state 90% of the time, that player may have a positive closing/pressure factor.

Reason:

- This helps separate genuine mentality/response from simply being a stronger or weaker player.

Important:

- Must only use matches before the current match to avoid leakage.
- Do not build a custom model from scratch yet.
- Improve through engineered player strength and player pressure-response features first.
- Later, consider sequence models only if full point-history features become useful.

---

## Future modelling ideas

Potential models:

- Logistic regression
- Random forest
- XGBoost / LightGBM / CatBoost
- Calibration model
- Sequence model later if using full point-history sequences

Evaluation metrics:

- Log loss
- Brier score
- Calibration curve
- Reliability by probability bucket
- Out-of-sample performance by date split

Important:

- Do not rely only on accuracy.
- Split by date or match, not random rows.
- Avoid leakage from future matches, future sets, or final results.
