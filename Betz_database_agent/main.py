from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).parent

POSSIBLE_DATA_DIRS = [
    BASE_DIR / "data",
    BASE_DIR / "Betz_database_agent" / "data",
]


def find_data_dir():
    for data_dir in POSSIBLE_DATA_DIRS:
        if data_dir.exists():
            return data_dir

    raise FileNotFoundError(
        "Could not find a data folder. Checked:\n"
        + "\n".join(str(path) for path in POSSIBLE_DATA_DIRS)
    )


DATA_DIR = find_data_dir()


def find_excel_file():
    excel_files = list(DATA_DIR.glob("*.xlsx"))

    if not excel_files:
        files_found = list(DATA_DIR.iterdir())
        raise FileNotFoundError(
            f"No .xlsx files found in {DATA_DIR}\n"
            f"Files found: {files_found}"
        )

    if len(excel_files) > 1:
        print("Multiple Excel files found. Using the first one:")
        for file in excel_files:
            print(f"- {file.name}")
        print()

    return excel_files[0]


DATA_FILE = find_excel_file()


def load_workbook():
    print(f"Loading file: {DATA_FILE}")
    print()

    return pd.read_excel(DATA_FILE, sheet_name=None)


def show_workbook_summary(sheets):
    print("Workbook loaded successfully")
    print()

    print("Sheets found:")
    for sheet_name, df in sheets.items():
        print(f"- {sheet_name}: {len(df)} rows, {len(df.columns)} columns")


def show_master_list(sheets):
    if "masterList" not in sheets:
        available_sheets = list(sheets.keys())
        raise KeyError(
            f"'masterList' sheet was not found. Available sheets: {available_sheets}"
        )

    master = sheets["masterList"]

    print()
    print("masterList columns:")
    for column in master.columns:
        print(f"- {column}")

    print()
    print("First 5 inventory rows:")
    print(master.head())


def main():
    sheets = load_workbook()
    show_workbook_summary(sheets)
    show_master_list(sheets)


if __name__ == "__main__":
    main()