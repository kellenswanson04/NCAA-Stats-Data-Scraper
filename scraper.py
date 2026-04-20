import pandas as pd

url = "https://hawaiiathletics.com/sports/baseball/stats/2026"
tables = pd.read_html(url)

# Simple toggles: set each mode to "on" or "off"
hitters = "on"
pitchers = "on"
fielders = "on"

totals = "off"


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

    if totals_mode.lower() == "off" and "Player" in clean_df.columns:
        excluded_names = {"totals", "opponents"}
        clean_df = clean_df[
            ~clean_df["Player"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(excluded_names)
        ]

    if "Player" in clean_df.columns:
        # Sort by last name using values from the Player column.
        player_series = clean_df["Player"].astype(str).str.strip()
        last_name = player_series.str.split(",").str[0].str.strip()
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

# Sidearm Sports pages usually order tables like this:
if hitters.lower() == "on":
    batting = prepare_stats_table(tables[0], totals, batting_decimal_rules)
    batting.to_csv("hitters.csv", index=False)

if pitchers.lower() == "on":
    pitching = prepare_stats_table(tables[1], totals, pitching_decimal_rules)
    pitching.to_csv("pitchers.csv", index=False)

if fielders.lower() == "on":
    fielding = prepare_stats_table(tables[2], totals, fielding_decimal_rules)
    fielding.to_csv("fielders.csv", index=False)