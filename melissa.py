import re  # Regex.
import sys

from collections import defaultdict
from csv import DictReader, DictWriter
from dataclasses import asdict, astuple, dataclass
from pathlib import Path

# Type hints:
from typing import Any, NamedTuple, Optional

if sys.version_info < (3, 9):
    # Deprecated import.
    from typing import Dict, Tuple
else:
    from builtins import dict as Dict, tuple as Tuple

# Fuzzy searching package.
# Use pip install easy-fuzzy
from fuzzy.collections import FuzzyFrozenDict

# The folder for everything:
#     Current directory: Path()
#     Relative directory: Path("subfolder")
#     Absolute directory: Path("C://directory path")
folder = Path("files")

# For parsing the address.
# Uses "regex" to parse data, assuming a consistent format is provided.
#
# Format assumed:
#     address = (street): (city) (state): (zip)(extra)
#     street = anything
#     city = anything
#     state = 2 letters
#     zip = 5 numbers
#     extra = anything
#
# Example:
#     store_address = "1300 Dana Dr: Redding CA: 96003-4071"
#     match = ADDRESS.compile(store_address)
#     if not match:
#         raise ValueError("failed to parse address: " + store_address)
#     address, city, state, zip = match.groups()
#     print(address, "|", city, "|", state, "|", zip)
#     # Build composite key.
#     key = Key("name", *match.groups()).upper()
#
# Output:
#     1300 Dana Dr | Redding | CA | 96003
#
STREET = "(?P<street>.*?)"
CITY = "(?P<city>.*?)"
STATE = "(?P<state>[a-zA-Z]{2})"
ZIP = "(?P<zip>[0-9]{5})"
ADDRESS = re.compile(f"{STREET}: {CITY} {STATE}: {ZIP}.*?")


class Key(NamedTuple):
    """
    A composite key storing the customer's name, address, city, state,
    and zip code.

    Example:
        key = Key(name, address, city, state, zip).clean()
        # Use in a dictionary:
        data = on_premise[key]

    Note:
        Cannot be modified.
    """
    customer_name: str
    address: str
    city: str
    state: str
    zip: str

    def clean(self):
        """Clean the key of whitespaces and make it upper case."""
        return Key(*[key.strip().upper() for key in self])


# Create something to store the data.
@dataclass
class Data:
    """
    Stores the customer's data, including the tdlinx, sold to, license
    number, channel, sub-channel, and which file(s) it came from.

    Example:
        data = Data()               # Default missing data.
        data.tdlinx = "123"         # Fills in the tdlinx field.
        data.update(channel="456")  # Also updates the data.
        other = Data()
        data.update(**asdict(other))  # Merge customer data.
    """
    tdlinx: Optional[str] = None
    sold_to: Optional[str] = None
    license_number: Optional[str] = None
    channel: Optional[str] = None
    sub_channel: Optional[str] = None
    is_in_spectra: bool = False
    is_in_gallo: bool = False
    is_in_ww: bool = False

    def update(self, **kwargs: Any) -> None:
        """
        Helper function for updating customer data with more data.

        Update with new variables:
            data.update(tdlinx="12345", channel="abcde")

        Update with another data object:
            data.update(**asdict(other))
        """
        if kwargs.get("tdlinx") is not None:
            self.tdlinx = kwargs.pop("tdlinx")
        if kwargs.get("sold_to") is not None:
            self.sold_to = kwargs.pop("sold_to")
        if kwargs.get("license_number") is not None:
            self.license_number = kwargs.pop("license_number")
        if kwargs.get("channel") is not None:
            self.channel = kwargs.pop("channel")
        if kwargs.get("sub_channel") is not None:
            self.sub_channel = kwargs.pop("sub_channel")
        self.is_in_spectra |= kwargs.get("is_in_spectra", False)
        self.is_in_gallo |= kwargs.get("is_in_gallo", False)
        self.is_in_ww |= kwargs.get("is_in_ww", False)


# Create the tables for storing results.
# Usage:
#     # Build the composite key.
#     key = Key(customer_name, address, city, state, zip).upper()
#
#     # Get the data for that customer.
#     data = on_premise[key]
#
#     # Update the data for that customer.
#     data.tdlinx = ...
#
#     # Loop through each row.
#     for key, data in on_premise.items():
#         # Build a csv row.
#         row = dict(zip(fieldnames, (*key, "On-Premise", *astuple(data))))
#
on_premise = defaultdict(Data)
off_premise = defaultdict(Data)

# Save the results to each file.
fieldnames = [
    "Customer Name",
    "Address",
    "City",
    "State",
    "Zip",
    "Premise",
    "TDLinx Code",
    "Sold to",
    "License No.",
    "Channel / Trad Channel",
    "Sub-Channel / Sub Trade Channel",
    "IN SPECTRA",
    "IN GALLO",
    "IN WW",
]

dupe_fieldnames = ["Dupe" + column for column in fieldnames[:len(Key._fields)]] + fieldnames

# Convert excel sheets to csv files.

# Load the Gallo file.
with open(folder / "gallo_on_premise.csv", mode="r", newline="", encoding="utf8") as file:
    # Use csv.DictReader to read each row.
    # https://docs.python.org/3/library/csv.html#csv.DictReader
    reader = DictReader(file)
    for row in reader:
        # Parse the address.
        address = row
        key = Key(row["Customer Name"], row["Address"], row["City"], row["State"], row["Zip"]).clean()
        on_premise[key].update(
            tdlinx=row["TDLinx Code"],
            channel = row["Channel"],
            sub_channel = row["Sub-Channel"],
            is_in_gallo = True,
        )

# Load the Spectra on-premise file.
with open(folder / "spectra_on_premise.csv", mode="r", newline="", encoding="utf8") as file:
    reader = DictReader(file)
    tdlinx_name = reader.fieldnames[0]
    for row in reader:
        # Parse the store address.
        match = ADDRESS.match(row["Store Address"])
        if not match:
            raise ValueError("failed to parse address: " + row["Store Address"])
        key = Key(row["Store Name"], *match.groups()).clean()
        on_premise[key].update(tdlinx=row[tdlinx_name], is_in_spectra=True)

# Load the Spectra on-premise file.
with open(folder / "spectra_off_premise.csv", mode="r", newline="", encoding="utf8") as file:
    reader = DictReader(file)
    tdlinx_name = reader.fieldnames[0]
    for row in reader:
        # Parse the store address.
        match = ADDRESS.match(row["Store Address"])
        if not match:
            raise ValueError("failed to parse address: " + row["Store Address"])
        key = Key(row["Store Name"], *match.groups()).clean()
        off_premise[key].update(tdlinx=row[tdlinx_name], is_in_spectra=True)

# Do the same for other files.
# Load the file. Convert excel sheets to csv files.
with open(folder / "ww_on_premise.csv", mode="r", newline="", encoding="utf8") as file:
    # Use csv.DictReader to read each row.
    # https://docs.python.org/3/library/csv.html#csv.DictReader
    reader = DictReader(file)
    for row in reader:
        key = Key(row["sold_to_name"], row["addrl1"], row["city"], "CA", row["zip"]).clean()
        on_premise[key].update(
            license_number = row['License No.'],
            sold_to = row['sold_to'],
            is_in_ww = True,
        )


# Do the same for other files.
# Load the file. Convert excel sheets to csv files.
with open(folder / "ww_off_premise.csv", mode="r", newline="", encoding="utf8") as file:
    # Use csv.DictReader to read each row.
    # https://docs.python.org/3/library/csv.html#csv.DictReader
    reader = DictReader(file)
    for row in reader:
        key = Key(row["sold_to_name"], row["addrl1"],
                  row["city"], "CA", row["zip"]).clean()
        off_premise[key].update(
            license_number = row['License No.'],
            sold_to = row['sold_to'],
            is_in_ww = True,
        )

# Remove empty csv rows.
empty = Key("", "", "", "", "")

if empty in on_premise:
    del on_premise[empty]

if empty in off_premise:
    del off_premise[empty]

def fuzzy_filter(
    customers: Dict[Key, Data],
    *,
    tolerance: float = 0.8,
) -> Tuple[Dict[Key, Data], Dict[Key, Dict[Key, Data]]]:
    """
    Helper function for filtering customer data with fuzzy searching
    for the name and address. The state and zip must match for merges.
    The name, address, and city are merged together into one string,
    and this string is then used for fuzzy searching within that state
    and zip code.

    Example:
        Data:
            Name     | Address            | City         | State | Zip
            ------------------------------------------------------------
            111 CLUB | 545 S IMPERIAL AVE | CALEXICO     | CA    | 92231
            1212     | 1212 3RD ST        | SANTA MONICA | CA    | 90401
            1212     | 1212 3RD STREET    | SANTA MONICA | CA    | 90401

        Group by (state, zip) and join (name + address + city):
            State | Zip   | Fuzzy Joined Column
            ------------------------------------------------------------
            CA    | 92231 | 111 CLUB | 545 S IMPERIAL AVE | CALEXICO
            ------------------------------------------------------------
            CA    | 90401 | 1212     | 1212 3RD ST        | SANTA MONICA
                            1212     | 1212 3RD STREET    | SANTA MONICA

        Fuzzy merge groups:
            State | Zip   | Fuzzy Joined Column
            ------------------------------------------------------------
            CA    | 92231 | 111 CLUB | 545 S IMPERIAL AVE | CALEXICO
            ------------------------------------------------------------
            CA    | 90401 | 1212     | 1212 3RD ST        | SANTA MONICA

        Recreate table:
            Name     | Address            | City         | State | Zip
            ------------------------------------------------------------
            111 CLUB | 545 S IMPERIAL AVE | CALEXICO     | CA    | 92231
            1212     | 1212 3RD ST        | SANTA MONICA | CA    | 90401

    Parameters:
        customers:
            The data for each customer stored in {key: data}.

    Returns:
        (customers, dupes):
            customers:
                A filtered dictionary for each customer stored in
                {key: merged_data}.
            dupes:
                A dictionary containing all of the duplicated
                information as {fuzzy_key: {key: data}}.
    """
    # Group by zip and state.
    by_zip = defaultdict(list)
    for key in customers:
        by_zip[key.state, key.zip].append(key)
    # Collect the results into a new dict.
    result = defaultdict(Data)
    dupes = defaultdict(lambda: defaultdict(Data))
    progress = 0
    # Loop through each group.
    for keys in by_zip.values():
        # Fuzzily merge by "name | address | city".
        D = FuzzyFrozenDict(
            (
                (f"{key.customer_name} | {key.address} | {key.city}", key)
                for key in keys
            ),
            tolerance=0.8,
        )
        # Loop through the unique fuzzy keys.
        for unique_key in D.fuzzy():
            # Update the final result.
            data = result[D[unique_key]]
            # Get similar keys.
            matches = D.fuzzy().matches(unique_key)
            for similar_key in matches:
                # Display the progress so far.
                progress += 1
                print(end=f"Progress: {progress / len(customers):6.1%}\r")
                # Get the unfuzzy key.
                key = D[similar_key]
                # Update the customer.
                data.update(**asdict(customers[key]))
                if len(matches) > 1:
                    dupes[D[unique_key]][key].update(**asdict(customers[key]))
    # Remove progress display.
    print(end="                \r")
    # Return results as a normal dictionary.
    return dict(result), dict(zip(dupes, map(dict, dupes.values())))


# Apply fuzzy filtering to the `on_premise` and `off_premise` dictionaries.
print("On premise:")
on_premise, on_premise_dupes = fuzzy_filter(on_premise)
print("Progress: 100.0%")
print("Off premise:")
off_premise, off_premise_dupes = fuzzy_filter(off_premise)
print("Progress: 100.0%")

# Save results to a csv file.
with open("On-Premise.csv", mode="w", newline="", encoding="utf8") as file:
    # Use csv.DictWriter to write each row.
    # https://docs.python.org/3/library/csv.html#csv.DictWriter
    writer = DictWriter(file, fieldnames)
    # Write the field names.
    writer.writeheader()
    # Write the rest of the rows.
    for key, data in sorted(on_premise.items()):
        # Build a csv row.
        row = dict(zip(fieldnames, (*key, "On-Premise", *astuple(data))))
        writer.writerow(row)

# Save dupes to a csv file.
with open("On-Premise-Dupes.csv", mode="w", newline="", encoding="utf8") as file:
    # Use csv.DictWriter to write each row.
    # https://docs.python.org/3/library/csv.html#csv.DictWriter
    writer = DictWriter(file, dupe_fieldnames)
    # Write the field names.
    writer.writeheader()
    # Write the rest of the rows.
    for unique_key, dupes in sorted(on_premise_dupes.items()):
        for key, data in dupes.items():
            # Build a csv row.
            row = dict(zip(dupe_fieldnames, (*unique_key, *key, "On-Premise", *astuple(data))))
            writer.writerow(row)

# Save results to a csv file.
with open("Off-Premise.csv", mode="w", newline="", encoding="utf8") as file:
    # Use csv.DictWriter to write each row.
    # https://docs.python.org/3/library/csv.html#csv.DictWriter
    writer = DictWriter(file, fieldnames)
    # Write the field names.
    writer.writeheader()
    # Write the rest of the rows.
    for key, data in sorted(off_premise.items()):
        # Build a csv row.
        row = dict(zip(fieldnames, (*key, "Off-Premise", *astuple(data))))
        writer.writerow(row)

# Save dupes to a csv file.
with open("Off-Premise-Dupes.csv", mode="w", newline="", encoding="utf8") as file:
    # Use csv.DictWriter to write each row.
    # https://docs.python.org/3/library/csv.html#csv.DictWriter
    writer = DictWriter(file, dupe_fieldnames)
    # Write the field names.
    writer.writeheader()
    # Write the rest of the rows.
    for unique_key, dupes in sorted(off_premise_dupes.items()):
        for key, data in dupes.items():
            # Build a csv row.
            row = dict(zip(dupe_fieldnames, (*unique_key, *key, "Off-Premise", *astuple(data))))
            writer.writerow(row)
