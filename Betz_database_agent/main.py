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
    return pd.read_excel(DATA_FILE, sheet_name=None)


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


def get_items_to_order(master):
    items_to_order = master[
        master["MinQty"].notna()
        & master["QtyOnHand"].notna()
        & (master["MinQty"] > 0)
        & (master["QtyOnHand"] < master["MinQty"])
    ].copy()

    items_to_order["NeededQty"] = (
        items_to_order["MinQty"] - items_to_order["QtyOnHand"]
    )

    return items_to_order


def get_items_to_watch(master):
    items_to_watch = master[
        master["MinQty"].notna()
        & master["QtyOnHand"].notna()
        & (master["MinQty"] > 0)
        & (master["QtyOnHand"] >= master["MinQty"])
        & (master["QtyOnHand"] <= master["MinQty"] + 1)
    ].copy()

    items_to_watch["QtyAboveMin"] = (
        items_to_watch["QtyOnHand"] - items_to_watch["MinQty"]
    )

    return items_to_watch


def search_inventory(master, search_text):
    searchable_columns = [
        "ItemID",
        "SKU",
        "Description",
        "Category",
        "Location",
        "Owner/Truck",
        "Notes",
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

    return matches


def get_items_by_location(master, location):
    location_text = location.lower()

    return master[
        master["Location"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(location_text, regex=False)
    ].copy()


def get_quantity_by_category(master):
    return (
        master.groupby("Category", dropna=False)["QtyOnHand"]
        .sum()
        .reset_index()
        .sort_values("QtyOnHand", ascending=False)
    )


def print_table(df, columns):
    if df.empty:
        print("No matching items found.")
        return

    print(df[columns].to_string(index=False))


def show_items_to_order(master):
    items_to_order = get_items_to_order(master)

    print()
    print("ITEMS TO ORDER")

    if items_to_order.empty:
        print("No items currently need to be ordered.")
        return

    print(f"{len(items_to_order)} items are below minimum quantity.")
    print()

    columns = [
        "ItemID",
        "Description",
        "Category",
        "QtyOnHand",
        "MinQty",
        "NeededQty",
        "Unit",
        "Location",
        "Owner/Truck",
    ]

    print_table(items_to_order, columns)


def show_items_to_watch(master):
    items_to_watch = get_items_to_watch(master)

    print()
    print("ITEMS TO WATCH")
    print("These items are at minimum quantity or only 1 above minimum quantity.")

    if items_to_watch.empty:
        print("No items are currently near minimum quantity.")
        return

    print(f"{len(items_to_watch)} items are near minimum quantity.")
    print()

    columns = [
        "ItemID",
        "Description",
        "Category",
        "QtyOnHand",
        "MinQty",
        "QtyAboveMin",
        "Unit",
        "Location",
        "Owner/Truck",
    ]

    print_table(items_to_watch, columns)


def show_search_results(master):
    search_text = input("Search for item, category, location, or owner/truck: ").strip()

    if not search_text:
        print("Search cancelled. No search text entered.")
        return

    matches = search_inventory(master, search_text)

    print()
    print(f"SEARCH RESULTS FOR: {search_text}")
    print(f"{len(matches)} matching items found.")
    print()

    columns = [
        "ItemID",
        "Description",
        "Category",
        "QtyOnHand",
        "Unit",
        "Location",
        "Owner/Truck",
    ]

    print_table(matches.head(25), columns)


def show_location_results(master):
    location = input("Enter location to search, like Shelf 1: ").strip()

    if not location:
        print("Location search cancelled. No location entered.")
        return

    matches = get_items_by_location(master, location)

    print()
    print(f"ITEMS IN LOCATION: {location}")
    print(f"{len(matches)} matching items found.")
    print()

    columns = [
        "ItemID",
        "Description",
        "Category",
        "QtyOnHand",
        "Unit",
        "Location",
        "Owner/Truck",
    ]

    print_table(matches.head(25), columns)


def show_category_summary(master):
    summary = get_quantity_by_category(master)

    print()
    print("QUANTITY ON HAND BY CATEGORY")
    print()
    print(summary.to_string(index=False))


def show_menu():
    print()
    print("BETZ DATABASE AGENT")
    print(f"Inventory file: {DATA_FILE.name}")
    print()
    print("What would you like to see?")
    print("1. Items that need to be ordered")
    print("2. Items at or near minimum")
    print("3. Search inventory")
    print("4. Items by location")
    print("5. Quantity by category")
    print("6. Exit")


def run_menu(master):
    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            show_items_to_order(master)
        elif choice == "2":
            show_items_to_watch(master)
        elif choice == "3":
            show_search_results(master)
        elif choice == "4":
            show_location_results(master)
        elif choice == "5":
            show_category_summary(master)
        elif choice == "6":
            print("Goodbye.")
            break
        else:
            print("Please choose 1, 2, 3, 4, 5, or 6.")


def main():
    sheets = load_workbook()
    master = get_master_list(sheets)

    run_menu(master)


if __name__ == "__main__":
    main()