import re
from collections import defaultdict
from csv import DictReader, DictWriter
from dataclasses import astuple, dataclass
from typing import NamedTuple, Optional

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


# For the composite key.
class Key(NamedTuple):
    customer_name: str
    address: str
    city: str
    state: str
    zip: str

    def upper(self):
        return Key(*[key.upper() for key in self])


# Create something to store the data.
@dataclass
class Data:
    tdlinx: Optional[int] = None
    sold_to: Optional[str] = None
    licence_number: Optional[str] = None
    channel: Optional[str] = None
    sub_channel: Optional[str] = None
    is_in_spectra: bool = False
    is_in_gallo: bool = False
    is_in_ww: bool = False


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
    "Licence No.",
    "Channel / Trad Channel",
    "Sub-Channel / Sub Trade Channel",
    "IN SPECTRA",
    "IN GALLO",
    "IN WW",
]

# Convert excel sheets to csv files.

# Load the Gallo file.
with open("gallo_on_premise.csv", mode="r", newline="") as file:
    # Use csv.DictReader to read each row.
    # https://docs.python.org/3/library/csv.html#csv.DictReader
    reader = DictReader(file)
    for row in reader:
        # Parse the address.
        address = row
        key = Key(row["Customer Name"], row["Address"],
                  row["City"], row["State"], row["Zip"]).upper()
        data = on_premise[key]
        data.tdlinx = row["TDLinx Code"]
        data.channel = row["Channel"]
        data.sub_channel = row["Sub-Channel"]
        data.is_in_gallow = True

# Load the Spectra on-premise file.
with open("spectra_on_premise.csv", mode="r", newline="") as file:
    reader = DictReader(file)
    tdlinx_name = reader.fieldnames[0]
    for row in reader:
        # Parse the store address.
        match = ADDRESS.match(row["Store Address"])
        if not match:
            raise ValueError("failed to parse address: " +
                             row["Store Address"])
        key = Key(row["Store Name"], *match.groups()).upper()
        data = on_premise[key]
        data.tdlinx = row[tdlinx_name]
        data.is_in_spectra = True

# Load the Spectra on-premise file.
with open("spectra_off_premise.csv", mode="r", newline="") as file:
    reader = DictReader(file)
    tdlinx_name = reader.fieldnames[0]
    for row in reader:
        # Parse the store address.
        match = ADDRESS.match(row["Store Address"])
        if not match:
            raise ValueError("failed to parse address: " +
                             row["Store Address"])
        key = Key(row["Store Name"], *match.groups()).upper()
        data = off_premise[key]
        data.tdlinx = row[tdlinx_name]
        data.is_in_spectra = True

# Do the same for other files.
# Load the file. Convert excel sheets to csv files.
with open("ww_on_premise.csv", mode="r", newline="") as file:
    # Use csv.DictReader to read each row.
    # https://docs.python.org/3/library/csv.html#csv.DictReader
    reader = DictReader(file)
    for row in reader:
        key = Key(row["sold_to_name"], row["addrl1"],
                  row["city"], "CA", row["zip"]).upper()
        data = on_premise[key]
        data.license_number = row['License No.']
        data.sold_to = row['sold_to']
        data.is_in_ww = True


# Do the same for other files.
# Load the file. Convert excel sheets to csv files.
with open("ww_off_premise.csv", mode="r", newline="") as file:
    # Use csv.DictReader to read each row.
    # https://docs.python.org/3/library/csv.html#csv.DictReader
    reader = DictReader(file)
    for row in reader:
        key = Key(row["sold_to_name"], row["addrl1"],
                  row["city"], "CA", row["zip"]).upper()
        data = off_premise[key]
        data.license_number = row['License No.']
        data.sold_to = row['sold_to']
        data.is_in_ww = True

# Save results to a csv file.
with open("On-Premise.csv", mode="w", newline="") as file:
    # Use csv.DictWriter to write each row.
    # https://docs.python.org/3/library/csv.html#csv.DictWriter
    writer = DictWriter(file, fieldnames)
    # Write the field names.
    writer.writeheader()
    # Write the rest of the rows.
    for key, value in on_premise.items():
        # Build a csv row.
        row = dict(zip(fieldnames, (*key, "On-Premise", *astuple(data))))
        writer.writerow(row)

# Save results to a csv file.
with open("Off-Premise.csv", mode="w", newline="") as file:
    # Use csv.DictWriter to write each row.
    # https://docs.python.org/3/library/csv.html#csv.DictWriter
    writer = DictWriter(file, fieldnames)
    # Write the field names.
    writer.writeheader()
    # Write the rest of the rows.
    for key, value in off_premise.items():
        # Build a csv row.
        row = dict(zip(fieldnames, (*key, "Off-Premise", *astuple(data))))
        writer.writerow(row)
