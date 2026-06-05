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
OVERRIDE_FILE = DATA_DIR / "quantity_overrides.csv"


def find_excel_file():
    excel_files = list(DATA_DIR.glob("*.xlsx"))

    if not excel_files:
        raise FileNotFoundError(f"No .xlsx files found in {DATA_DIR}")

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
        raise KeyError(
            f"'masterList' was not found. Available sheets: {list(sheets.keys())}"
        )

    master = sheets["masterList"].copy()

    master["ItemID"] = master["ItemID"].fillna("").astype(str)
    master["QtyOnHand"] = pd.to_numeric(master["QtyOnHand"], errors="coerce")
    master["MinQty"] = pd.to_numeric(master["MinQty"], errors="coerce")

    return apply_quantity_overrides(master)


def apply_quantity_overrides(master):
    if not OVERRIDE_FILE.exists():
        return master

    overrides = pd.read_csv(OVERRIDE_FILE)
    overrides["ItemID"] = overrides["ItemID"].astype(str)
    overrides["QtyOnHand"] = pd.to_numeric(
        overrides["QtyOnHand"],
        errors="coerce",
    )

    override_quantities = overrides.set_index("ItemID")["QtyOnHand"]

    master["QtyOnHand"] = master["ItemID"].map(
        override_quantities
    ).fillna(master["QtyOnHand"])

    return master


def save_quantity_override(item_id, quantity):
    if OVERRIDE_FILE.exists():
        overrides = pd.read_csv(OVERRIDE_FILE)
    else:
        overrides = pd.DataFrame(columns=["ItemID", "QtyOnHand"])

    overrides["ItemID"] = overrides["ItemID"].astype(str)

    existing = overrides["ItemID"].str.lower() == item_id.lower()

    if existing.any():
        overrides.loc[existing, "QtyOnHand"] = quantity
    else:
        new_override = pd.DataFrame(
            [{"ItemID": item_id, "QtyOnHand": quantity}]
        )
        overrides = pd.concat([overrides, new_override], ignore_index=True)

    overrides.to_csv(OVERRIDE_FILE, index=False)


def get_items_to_order(master):
    items = master[
        master["MinQty"].notna()
        & master["QtyOnHand"].notna()
        & (master["MinQty"] > 0)
        & (master["QtyOnHand"] < master["MinQty"])
    ].copy()

    items["NeededQty"] = items["MinQty"] - items["QtyOnHand"]

    return items


def get_items_to_watch(master):
    items = master[
        master["MinQty"].notna()
        & master["QtyOnHand"].notna()
        & (master["MinQty"] > 0)
        & (master["QtyOnHand"] >= master["MinQty"])
        & (master["QtyOnHand"] <= master["MinQty"] + 1)
    ].copy()

    items["QtyAboveMin"] = items["QtyOnHand"] - items["MinQty"]

    return items


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

    return master[
        master[searchable_columns]
        .fillna("")
        .astype(str)
        .apply(
            lambda row: row.str.contains(
                search_text,
                case=False,
                regex=False,
            ).any(),
            axis=1,
        )
    ]


def get_items_by_location(master, location):
    return master[
        master["Location"]
        .fillna("")
        .astype(str)
        .str.contains(location, case=False, regex=False)
    ].copy()


def get_quantity_by_category(master):
    return (
        master.groupby("Category", dropna=False)["QtyOnHand"]
        .sum()
        .reset_index()
        .sort_values("QtyOnHand", ascending=False)
    )


def inventory_columns():
    return [
        "ItemID",
        "Description",
        "Category",
        "QtyOnHand",
        "Unit",
        "Location",
        "Owner/Truck",
    ]


def print_table(dataframe, columns):
    if dataframe.empty:
        print("No matching items found.")
        return

    print(dataframe[columns].to_string(index=False))


def show_items_to_order(master):
    items = get_items_to_order(master)

    print("\nITEMS TO ORDER")

    if items.empty:
        print("No items currently need to be ordered.")
        return

    print(f"{len(items)} items are below minimum quantity.\n")

    columns = inventory_columns() + ["MinQty", "NeededQty"]
    print_table(items, columns)


def show_items_to_watch(master):
    items = get_items_to_watch(master)

    print("\nITEMS TO WATCH")
    print("Items at minimum or only 1 above minimum.\n")

    columns = inventory_columns() + ["MinQty", "QtyAboveMin"]
    print_table(items, columns)


def show_search_results(master):
    search_text = input("Enter item, category, location, or owner: ").strip()

    if not search_text:
        print("Search cancelled.")
        return

    matches = search_inventory(master, search_text)

    print(f"\nSEARCH RESULTS FOR: {search_text}")
    print(f"{len(matches)} matching items found.\n")
    print_table(matches.head(25), inventory_columns())


def show_location_results(master):
    location = input("Enter a location, such as Shelf 1: ").strip()

    if not location:
        print("Location search cancelled.")
        return

    matches = get_items_by_location(master, location)

    print(f"\nITEMS IN LOCATION: {location}")
    print(f"{len(matches)} matching items found.\n")
    print_table(matches.head(25), inventory_columns())


def show_category_summary(master):
    print("\nQUANTITY ON HAND BY CATEGORY\n")
    print(get_quantity_by_category(master).to_string(index=False))


def manually_update_quantity(master):
    search_text = input(
        "Enter the ItemID or description of the item to update: "
    ).strip()

    if not search_text:
        print("Update cancelled.")
        return

    matches = search_inventory(master, search_text)

    if matches.empty:
        print("No matching items found.")
        return

    print("\nMATCHING ITEMS\n")
    print_table(matches.head(25), inventory_columns())

    item_id = input("\nEnter the exact ItemID to update: ").strip()

    item_match = master["ItemID"].str.lower() == item_id.lower()

    if not item_match.any():
        print(f"ItemID '{item_id}' was not found.")
        return

    item = master.loc[item_match].iloc[0]

    print(
        f"\nSelected: {item['ItemID']} - {item['Description']}"
        f"\nCurrent quantity: {item['QtyOnHand']}"
    )

    quantity_text = input("Enter the new quantity: ").strip()

    try:
        new_quantity = float(quantity_text)
    except ValueError:
        print("Quantity must be a number.")
        return

    if new_quantity < 0:
        print("Quantity cannot be negative.")
        return

    confirmation = input(
        f"Change {item['ItemID']} quantity to {new_quantity}? (y/n): "
    ).strip().lower()

    if confirmation != "y":
        print("Update cancelled.")
        return

    save_quantity_override(item["ItemID"], new_quantity)
    master.loc[item_match, "QtyOnHand"] = new_quantity

    print(f"Quantity updated to {new_quantity}.")
    print(f"Override saved to: {OVERRIDE_FILE.name}")


def show_menu():
    print("\nBETZ DATABASE AGENT")
    print(f"Inventory file: {DATA_FILE.name}")

    if OVERRIDE_FILE.exists():
        print(f"Overrides file: {OVERRIDE_FILE.name}")

    print("\nWhat would you like to see?")
    print("1. Items that need to be ordered")
    print("2. Items at or near minimum")
    print("3. Search inventory")
    print("4. Items by location")
    print("5. Quantity by category")
    print("6. Manually update an item quantity")
    print("7. Exit")


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
            manually_update_quantity(master)
        elif choice == "7":
            print("Goodbye.")
            break
        else:
            print("Please choose an option from 1 through 7.")


def main():
    sheets = load_workbook()
    master = get_master_list(sheets)

    run_menu(master)


if __name__ == "__main__":
    main()