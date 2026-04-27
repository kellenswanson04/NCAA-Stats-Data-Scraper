import pandas as pd
import re

# Trackman Team Name
team_name = "CAL_MAT"
url = "https://hawaiiathletics.com/sports/baseball/stats/2026"
tables = pd.read_html(url)

# Toggles
trackman = "on"
hitters = "off"
pitchers = "on"
fielders = "off"
totals = "off"


def classify_table(df):
    columns = set(df.columns)
    if 'AVG' in columns and 'OPS' in columns:
        return 'batting'
    elif 'ERA' in columns or 'WHIP' in columns:
        return 'pitching'
    elif 'FLD%' in columns:
        return 'fielding'
    else:
        return 'unknown'


def format_decimal_columns(df, decimal_rules):
    for col, decimals in decimal_rules.items():
        if col not in df.columns:
            continue

        numeric_values = pd.to_numeric(df[col], errors="coerce")
        formatted_values = numeric_values.map(
            lambda x: f"{x:.{decimals}f}" if pd.notna(x) else ""
        )
        original_values = df[col].astype(str).str.strip()
        df[col] = formatted_values.where(numeric_values.notna(), original_values)

    return df


def prepare_stats_table(df, totals_mode, decimal_rules):
    clean_df = df.copy()

    if "Player" in clean_df.columns:
        def clean_player_cell(val):
            val = str(val).strip()
            
            # Extract the first "Last, First" pattern using regex
            match = re.search(r'([A-Za-z\s]+),\s*([A-Za-z\s]+)', val)
            if match:
                last_name, first_name = match.groups()
                return f"{last_name.strip()}, {first_name.strip()}"
            
            # Fallback: if no match, return stripped value
            return val

        clean_df["Player"] = clean_df["Player"].apply(clean_player_cell)

    if totals_mode.lower() == "off" and "Player" in clean_df.columns:
        excluded_names = {"totals", "opponents"}
        clean_df = clean_df[
            ~clean_df["Player"]
            .astype(str)
            .str.strip()
            .str.lower()
            .str.contains("total|opponent", na=False)
        ]

    if "Player" in clean_df.columns:
        # Sort by last name using the now-cleaned Player column.
        player_series = clean_df["Player"].astype(str).str.strip()
        last_name = player_series.str.split(",").str[0].str.strip()
        
        # Fallback for names without commas
        no_comma_mask = ~player_series.str.contains(",", na=False)
        last_name.loc[no_comma_mask] = (
            player_series[no_comma_mask].str.split().str[-1].str.strip()
        )

        clean_df = clean_df.assign(_last_name_sort=last_name.str.lower())
        clean_df = clean_df.sort_values("_last_name_sort", kind="stable")
        clean_df = clean_df.drop(columns="_last_name_sort")
        clean_df = clean_df.reset_index(drop=True)

    # Prevent Excel from auto-converting stats like "3-1" into dates.
    dash_stat_pattern = r"^\d{1,2}-\d{1,2}$"
    object_columns = clean_df.select_dtypes(include=["object"]).columns
    for col in object_columns:
        as_text = clean_df[col].astype(str).str.strip()
        mask = as_text.str.fullmatch(dash_stat_pattern, na=False)
        clean_df.loc[mask, col] = '="' + as_text[mask] + '"'

    clean_df = format_decimal_columns(clean_df, decimal_rules)

    return clean_df

def apply_trackman_team_column(df, trackman_mode, team_value, column_name):
    if trackman_mode.lower() != "on":
        return df

    with_team = df.copy()
    if column_name in with_team.columns:
        with_team = with_team.drop(columns=[column_name])
    with_team.insert(0, column_name, team_value)
    return with_team


pitching_decimal_rules = {
    "ERA": 2,
    "WHIP": 2,
    "IP": 1,
    "B/AVG": 3,
}

batting_decimal_rules = {
    "AVG": 3,
    "OPS": 3,
    "SLG%": 3,
    "OB%": 3,
}

fielding_decimal_rules = {
    "FLD%": 3,
}

# Classify and collect tables
classified_tables = {}
for i, table in enumerate(tables):
    table_type = classify_table(table)
    if table_type != 'unknown' and table_type not in classified_tables:
        classified_tables[table_type] = table

# Process and save based on toggles
if hitters.lower() == "on" and 'batting' in classified_tables:
    batting = prepare_stats_table(classified_tables['batting'], totals, batting_decimal_rules)
    batting = apply_trackman_team_column(
        batting, trackman, team_name, "BatterTeam"
    )
    batting.to_csv("hitters.csv", index=False)

if pitchers.lower() == "on" and 'pitching' in classified_tables:
    pitching = prepare_stats_table(classified_tables['pitching'], totals, pitching_decimal_rules)
    pitching = apply_trackman_team_column(
        pitching, trackman, team_name, "PitcherTeam"
    )
    pitching.to_csv("pitchers.csv", index=False)

if fielders.lower() == "on" and 'fielding' in classified_tables:
    fielding = prepare_stats_table(classified_tables['fielding'], totals, fielding_decimal_rules)
    fielding = apply_trackman_team_column(
        fielding, trackman, team_name, "FielderTeam"
    )
    fielding.to_csv("fielders.csv", index=False)