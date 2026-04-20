# NCAA Stats Data Scraper

A lightweight Python scraper that pulls team baseball statistics from Sidearm Sports pages and exports clean CSV files for batting, pitching, and fielding.

## Features

- Independent `on/off` mode toggles for:
  - Hitters
  - Pitchers
  - Fielders
- Optional `totals` toggle to include or exclude `Totals` and `Opponents` rows
- Alphabetical player sorting by last name (from the `Player` column)
- Separate CSV outputs:
  - `hitters.csv`
  - `pitchers.csv`
  - `fielders.csv`
- Excel-safe handling for values like `3-1` to prevent accidental date conversion
- Fixed decimal formatting for key stats:
  - Pitchers: `ERA` (2), `WHIP` (2), `IP` (1), `B/AVG` (3)
  - Batters: `AVG` (3), `OPS` (3), `SLG%` (3), `OB%` (3)
  - Fielders: `FLD%` (3)

## Requirements

- Python 3.9+
- `pandas`
- Internet access (to fetch stats tables)

## Installation

1. Clone or download this project.
2. Install dependencies:

```bash
pip install pandas
```

## Configuration

Open `scraper.py` and set the toggles:

- `hitters = "on"` or `"off"`
- `pitchers = "on"` or `"off"`
- `fielders = "on"` or `"off"`
- `totals = "on"` or `"off"`

Update the `url` variable to the team/year stats page you want to scrape.

## Usage

Run:

```bash
python scraper.py
```

Generated CSV files will be written to the project folder based on enabled modes.

## Notes

- The script assumes Sidearm Sports table order:
  - Batting = table index `0`
  - Pitching = table index `1`
  - Fielding = table index `2`
- If a table is missing expected columns, the script safely skips formatting for columns that are not present.

## Credit

Built and maintained by Swan, with development support from Cursor.
