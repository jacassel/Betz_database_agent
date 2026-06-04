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


def get_master_list(sheets):
    if "masterList" not in sheets:
        available_sheets = list(sheets.keys())
        raise KeyError(
            f"'masterList' sheet was not found. Available sheets: {available_sheets}"
        )

    master = sheets["masterList"].copy()

    master["QtyOnHand"] = pd.to_numeric(master["QtyOnHand"], errors="coerce")
    master["MinQty"] = pd.to_numeric(master["MinQty"], errors="coerce")

    return master


def show_master_list_preview(master):
    print()
    print("masterList columns:")
    for column in master.columns:
        print(f"- {column}")

    print()
    print("First 5 inventory rows:")
    print(master.head())


def show_low_stock_items(master):
    low_stock = master[
        master["MinQty"].notna()
        & master["QtyOnHand"].notna()
        & (master["QtyOnHand"] <= master["MinQty"])
    ]

    print()
    print("Question: Which items are at or below minimum quantity?")
    print(f"Answer: {len(low_stock)} items are at or below minimum quantity.")

    columns = ["ItemID", "Description", "Category", "QtyOnHand", "MinQty", "Location"]
    print(low_stock[columns].head(10))


def search_inventory(master, search_text):
    searchable_columns = [
        "ItemID",
        "SKU",
        "Description",
        "Category",
        "Location",
        "Owner/Truck",
    ]

    search_text = search_text.lower()

    matches = master[
        master[searchable_columns]
        .fillna("")
        .astype(str)
        .apply(
            lambda row: row.str.lower().str.contains(search_text, regex=False).any(),
            axis=1,
        )
    ]

    print()
    print(f"Question: Which inventory items match '{search_text}'?")
    print(f"Answer: Found {len(matches)} matching items.")

    columns = ["ItemID", "Description", "Category", "QtyOnHand", "Unit", "Location"]
    print(matches[columns].head(10))


def show_items_by_location(master, location):
    location_text = location.lower()

    matches = master[
        master["Location"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(location_text, regex=False)
    ]

    print()
    print(f"Question: Which items are in location '{location}'?")
    print(f"Answer: Found {len(matches)} items in matching locations.")

    columns = ["ItemID", "Description", "Category", "QtyOnHand", "Unit", "Location"]
    print(matches[columns].head(10))


def show_quantity_by_category(master):
    summary = (
        master.groupby("Category", dropna=False)["QtyOnHand"]
        .sum()
        .reset_index()
        .sort_values("QtyOnHand", ascending=False)
    )

    print()
    print("Question: What quantity is on hand by category?")
    print("Answer:")
    print(summary.head(15))


def answer_starter_questions(master):
    show_low_stock_items(master)
    search_inventory(master, "air filter")
    show_items_by_location(master, "Shelf 1")
    show_quantity_by_category(master)


def main():
    sheets = load_workbook()
    show_workbook_summary(sheets)

    master = get_master_list(sheets)
    show_master_list_preview(master)
    answer_starter_questions(master)


if __name__ == "__main__":
    main()