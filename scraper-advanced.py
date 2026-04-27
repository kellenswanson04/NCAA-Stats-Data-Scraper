from playwright.sync_api import sync_playwright
import pandas as pd
from io import StringIO
import time
import re

# Trackman Team Name
team_name = "CAL_MAT"
url = "https://gomatadors.com/sports/baseball/stats/2026"

# Toggles
trackman = "on"
hitters = "on"
pitchers = "on"
fielders = "on"
totals = "off"

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

def scrape_2026_all_columns():
    # Mapping suffixes to names for logic
    categories = {"0": "Batting", "1": "Pitching", "2": "Fielding"}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Opening 2026 Stats Page...")
        page.goto(url, wait_until="domcontentloaded")
        
        # 1. Clear UI Obstacles (Cookie banner & privacy overlays)
        page.evaluate("() => document.querySelectorAll('[class*=\"osano\"], [class*=\"cookie\"]').forEach(el => el.remove())")

        scraped_tables = {}
        for suffix, name in categories.items():
            print(f"\n--- Scraping ALL {name} Data ---")
            try:
                # 2. Targeted Menu Interaction
                stats_dropdown = page.get_by_label("Second Menu Options")
                stats_dropdown.click()
                time.sleep(1)

                # Use the aria-controls to find the exact list associated with the stats menu
                menu_id = stats_dropdown.get_attribute("aria-controls")
                page.locator(f"ul#{menu_id} li[id$='-{suffix}']").click()
                
                # 3. Verification: Wait for the button text to update to the name
                page.wait_for_selector(f"button[aria-label='Second Menu Options'] span:has-text('{name}')", timeout=10000)
                
                # Buffer for table rendering
                time.sleep(2) 

                # 4. Data Extraction
                html_content = page.content()
                all_tables = pd.read_html(StringIO(html_content))
                
                # Identify the correct table based on a unique keyword for each category
                keyword = "ERA" if name == "Pitching" else "FLD%" if name == "Fielding" else "AVG"
                target_df = None
                
                for df in all_tables:
                    # Flatten multi-index headers (common in Sidearm Sports tables)
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [' '.join(col).strip() for col in df.columns.values]
                    
                    cols_str = " ".join([str(c).upper() for c in df.columns])
                    if keyword in cols_str:
                        target_df = df
                        break

                if target_df is not None:
                    scraped_tables[name.lower()] = target_df
                    print(f"Successfully scraped {name} data with {len(target_df.columns)} columns")
                else:
                    print(f"Could not find the {name} data table.")

            except Exception as e:
                print(f"Error during {name}: {e}")
                page.screenshot(path=f"full_data_error_{name}.png")

        browser.close()

        # Process and save based on toggles
        if hitters.lower() == "on" and 'batting' in scraped_tables:
            batting = prepare_stats_table(scraped_tables['batting'], totals, batting_decimal_rules)
            batting = apply_trackman_team_column(
                batting, trackman, team_name, "BatterTeam"
            )
            batting.to_csv("hitters.csv", index=False)
            print("Saved hitters.csv")

        if pitchers.lower() == "on" and 'pitching' in scraped_tables:
            pitching = prepare_stats_table(scraped_tables['pitching'], totals, pitching_decimal_rules)
            pitching = apply_trackman_team_column(
                pitching, trackman, team_name, "PitcherTeam"
            )
            pitching.to_csv("pitchers.csv", index=False)
            print("Saved pitchers.csv")

        if fielders.lower() == "on" and 'fielding' in scraped_tables:
            fielding = prepare_stats_table(scraped_tables['fielding'], totals, fielding_decimal_rules)
            fielding = apply_trackman_team_column(
                fielding, trackman, team_name, "FielderTeam"
            )
            fielding.to_csv("fielders.csv", index=False)
            print("Saved fielders.csv")

if __name__ == "__main__":
    scrape_2026_all_columns()