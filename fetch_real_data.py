"""
fetch_real_data.py - Fetch real Hong Kong transport data from government APIs.

Data sources:
  - MTR stations and line topology: opendata.mtr.com.hk (CSV)
  - MTR adult Octopus fares:        opendata.mtr.com.hk (CSV)
  - Bus/Minibus segments:           hand-curated from official route info
  - Walking segments:               hand-curated (no API exists)
  - MTR travel times:               estimated from public timetables
  - MTR station coordinates:        public geographic data

Network scope: ~36 core stations covering ISL, TWL, KTL, TKL, EAL, TML,
SIL, and TCL lines, plus bus/minibus/walking connections.

Requires: Python 3.10+, internet access.  Uses only the standard library.
"""

import csv
import io
import os
import urllib.request

from models import Stop, Segment, TransportNetwork
from file_io import save_network

# ================================================================
#  Constants
# ================================================================

MTR_STATIONS_URL = "https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv"
MTR_FARES_URL = "https://opendata.mtr.com.hk/data/mtr_lines_fares.csv"

OUTPUT_DIR = "data"
OUTPUT_FILENAME = "hk_network_real.txt"

SELECTED_LINES = ["ISL", "TWL", "KTL", "TKL", "EAL", "TML", "SIL", "TCL"]

# Only keep these station codes (core urban network, ~36 stations)
SELECTED_STATIONS = {
    "KET", "SHW", "CEN", "ADM", "WAC", "CAB", "NOP", "QUB",
    "TSW", "LAK", "MEF", "SSP", "PRE", "MOK", "YMT", "JOR", "TST",
    "WHA", "HOM", "SKM", "KOT", "DIH",
    "TKO", "TIK",
    "SHT", "TAW", "MKK", "HUH",
    "ETS", "AUS", "NAC",
    "OCP", "SOH",
    "HOK", "KOW", "OLY",
}

# Adjacency per line (selected stations only, in travel order).
# Skipped intermediate stations are collapsed into one segment with
# aggregated travel time and the real OD fare from the API.
LINE_ADJACENCY = {
    "ISL": ["KET", "SHW", "CEN", "ADM", "WAC", "CAB", "NOP", "QUB"],
    "TWL": ["TSW", "LAK", "MEF", "SSP", "PRE", "MOK", "YMT",
             "JOR", "TST", "ADM", "CEN"],
    "KTL": ["WHA", "HOM", "YMT", "MOK", "PRE", "SKM", "KOT", "DIH"],
    "TKL": ["TKO", "TIK", "QUB", "NOP"],
    "EAL": ["SHT", "TAW", "KOT", "MKK", "HUH", "ADM"],
    "TML": ["MEF", "NAC", "AUS", "ETS", "HUH", "HOM", "DIH", "TAW"],
    "SIL": ["SOH", "OCP", "ADM"],
    "TCL": ["HOK", "KOW", "OLY", "NAC", "LAK"],
}

# ================================================================
#  Station coordinates (not available from API)
# ================================================================

MTR_STATION_COORDS = {
    "CEN": (22.2820, 114.1588), "ADM": (22.2793, 114.1654),
    "WAC": (22.2783, 114.1747), "CAB": (22.2800, 114.1840),
    "NOP": (22.2914, 114.2004), "QUB": (22.2884, 114.2093),
    "SHW": (22.2866, 114.1516), "KET": (22.2813, 114.1286),
    "TST": (22.2974, 114.1722), "JOR": (22.3049, 114.1718),
    "YMT": (22.3133, 114.1708), "MOK": (22.3193, 114.1694),
    "PRE": (22.3245, 114.1684), "SSP": (22.3309, 114.1623),
    "MEF": (22.3380, 114.1368), "LAK": (22.3485, 114.1257),
    "TSW": (22.3684, 114.1099), "SKM": (22.3316, 114.1740),
    "KOT": (22.3372, 114.1760), "DIH": (22.3394, 114.2015),
    "HOM": (22.3095, 114.1833), "WHA": (22.3047, 114.1897),
    "TKO": (22.3045, 114.2599), "TIK": (22.3045, 114.2527),
    "SHT": (22.3825, 114.1878), "TAW": (22.3726, 114.1785),
    "MKK": (22.3217, 114.1723), "HUH": (22.3028, 114.1814),
    "ETS": (22.2953, 114.1747), "AUS": (22.3041, 114.1666),
    "NAC": (22.3264, 114.1538), "SOH": (22.2425, 114.1490),
    "OCP": (22.2489, 114.1745), "HOK": (22.2850, 114.1585),
    "KOW": (22.3048, 114.1615), "OLY": (22.3178, 114.1602),
}

# ================================================================
#  Estimated travel times (minutes) between adjacent selected stations.
#  Where stations were skipped, times are summed.
#  Default for unlisted pairs: 3 minutes.
# ================================================================

DEFAULT_ADJACENT_TIME = 3

MTR_TRAVEL_TIMES = {
    ("KET", "SHW"): 6, ("SHW", "KET"): 6,
    ("SHW", "CEN"): 3, ("CEN", "SHW"): 3,
    ("CEN", "ADM"): 2, ("ADM", "CEN"): 2,
    ("ADM", "WAC"): 2, ("WAC", "ADM"): 2,
    ("WAC", "CAB"): 2, ("CAB", "WAC"): 2,
    ("CAB", "NOP"): 6, ("NOP", "CAB"): 6,
    ("NOP", "QUB"): 3, ("QUB", "NOP"): 3,
    ("TSW", "LAK"): 12, ("LAK", "TSW"): 12,
    ("LAK", "MEF"): 3, ("MEF", "LAK"): 3,
    ("MEF", "SSP"): 8, ("SSP", "MEF"): 8,
    ("SSP", "PRE"): 2, ("PRE", "SSP"): 2,
    ("PRE", "MOK"): 2, ("MOK", "PRE"): 2,
    ("MOK", "YMT"): 2, ("YMT", "MOK"): 2,
    ("YMT", "JOR"): 2, ("JOR", "YMT"): 2,
    ("JOR", "TST"): 2, ("TST", "JOR"): 2,
    ("TST", "ADM"): 4, ("ADM", "TST"): 4,
    ("WHA", "HOM"): 2, ("HOM", "WHA"): 2,
    ("HOM", "YMT"): 4, ("YMT", "HOM"): 4,
    ("SKM", "KOT"): 2, ("KOT", "SKM"): 2,
    ("KOT", "DIH"): 8, ("DIH", "KOT"): 8,
    ("TKO", "TIK"): 3, ("TIK", "TKO"): 3,
    ("TIK", "QUB"): 7, ("QUB", "TIK"): 7,
    ("SHT", "TAW"): 4, ("TAW", "SHT"): 4,
    ("TAW", "KOT"): 5, ("KOT", "TAW"): 5,
    ("KOT", "MKK"): 4, ("MKK", "KOT"): 4,
    ("MKK", "HUH"): 4, ("HUH", "MKK"): 4,
    ("HUH", "ADM"): 8, ("ADM", "HUH"): 8,
    ("MEF", "NAC"): 3, ("NAC", "MEF"): 3,
    ("NAC", "AUS"): 3, ("AUS", "NAC"): 3,
    ("AUS", "ETS"): 2, ("ETS", "AUS"): 2,
    ("ETS", "HUH"): 2, ("HUH", "ETS"): 2,
    ("HUH", "HOM"): 3, ("HOM", "HUH"): 3,
    ("HOM", "DIH"): 8, ("DIH", "HOM"): 8,
    ("DIH", "TAW"): 7, ("TAW", "DIH"): 7,
    ("SOH", "OCP"): 4, ("OCP", "SOH"): 4,
    ("OCP", "ADM"): 4, ("ADM", "OCP"): 4,
    ("HOK", "KOW"): 5, ("KOW", "HOK"): 5,
    ("KOW", "OLY"): 3, ("OLY", "KOW"): 3,
    ("OLY", "NAC"): 3, ("NAC", "OLY"): 3,
    ("NAC", "LAK"): 4, ("LAK", "NAC"): 4,
}

# ================================================================
#  Walking segments (hand-curated, bidirectional, cost $0)
# ================================================================

WALKING_SEGMENTS = [
    ("CEN", "HOK", 10),   # Central <-> Hong Kong station (IFC corridor)
    ("TST", "ETS", 5),    # TST <-> East TST (underground passage)
    ("MOK", "MKK", 8),    # Mong Kok <-> Mong Kok East (street)
    ("JOR", "AUS", 10),   # Jordan <-> Austin (street)
    ("ADM", "WAC", 15),   # Admiralty <-> Wan Chai (Harcourt Rd)
    ("TST", "YMT", 12),   # TST <-> Yau Ma Tei (Nathan Rd)
]

# ================================================================
#  Bus segments (hand-curated from official route information)
#  Format: (from, to, duration_min, cost_hkd)
#  These connect existing MTR stations via real bus routes.
# ================================================================

BUS_SEGMENTS = [
    # Cross-harbour routes (101, 104, 170 etc.)
    ("CEN", "TST", 20, 6.8),
    ("TST", "CEN", 20, 6.8),
    ("ADM", "TST", 15, 6.8),
    ("TST", "ADM", 15, 6.8),
    ("CEN", "MOK", 30, 10.2),
    ("MOK", "CEN", 30, 10.2),
    ("SHT", "ADM", 40, 12.4),
    ("ADM", "SHT", 40, 12.4),
    # Island corridor
    ("CEN", "CAB", 15, 4.2),
    ("CAB", "CEN", 15, 4.2),
    # Kowloon / NT connectors
    ("SHT", "MOK", 25, 8.5),
    ("MOK", "SHT", 25, 8.5),
    ("TST", "TSW", 30, 9.0),
    ("TSW", "TST", 30, 9.0),
    # TKO connector
    ("CAB", "TKO", 35, 9.8),
    ("TKO", "CAB", 35, 9.8),
]

# ================================================================
#  Minibus segments (hand-curated)
# ================================================================

MINIBUS_SEGMENTS = [
    ("CEN", "WAC", 10, 3.5),
    ("WAC", "CEN", 10, 3.5),
    ("TST", "MOK", 8, 4.0),
    ("MOK", "TST", 8, 4.0),
]


# ================================================================
#  Helper functions
# ================================================================

def _fetch_url(url, timeout=15):
    """Fetch URL content as string."""
    req = urllib.request.Request(url, headers={"User-Agent": "COMP1110-Project/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


# ================================================================
#  MTR data fetching
# ================================================================

def fetch_mtr_station_names():
    """
    Fetch station code -> English name mapping from official CSV.
    Only returns stations in SELECTED_STATIONS.
    """
    print("    Fetching MTR station names...")
    text = _fetch_url(MTR_STATIONS_URL)
    reader = csv.DictReader(io.StringIO(text))
    code_to_name = {}
    code_to_id = {}
    for row in reader:
        code = row["Station Code"].strip()
        if code in SELECTED_STATIONS:
            code_to_name[code] = row["English Name"].strip()
            code_to_id[code] = row["Station ID"].strip()
    print(f"    -> {len(code_to_name)} stations matched")
    return code_to_name, code_to_id


def fetch_mtr_fares(code_to_id):
    """
    Fetch real adult Octopus fares between selected station pairs.
    Returns dict: (from_code, to_code) -> fare_hkd
    """
    print("    Fetching MTR fares...")
    text = _fetch_url(MTR_FARES_URL)
    reader = csv.DictReader(io.StringIO(text))

    id_to_code = {v: k for k, v in code_to_id.items()}

    fares = {}
    for row in reader:
        src_id = row["SRC_STATION_ID"].strip()
        dst_id = row["DEST_STATION_ID"].strip()
        src_code = id_to_code.get(src_id)
        dst_code = id_to_code.get(dst_id)
        if not src_code or not dst_code or src_id == dst_id:
            continue
        try:
            fare = float(row["OCT_ADT_FARE"].strip())
            fares[(src_code, dst_code)] = fare
        except (ValueError, KeyError):
            continue
    print(f"    -> {len(fares)} fare pairs loaded")
    return fares


# ================================================================
#  Network assembly
# ================================================================

def build_network(code_to_name, fares):
    """
    Assemble a TransportNetwork from API fares + hardcoded data.

    Steps:
      1. Add stops (names from API, coordinates from hardcoded table).
      2. Add MTR segments per LINE_ADJACENCY with real fares and
         estimated travel times.
      3. Add bus, minibus, and walking segments.
    """
    network = TransportNetwork()

    # 1. Stops
    print("    Building stops...")
    for code in sorted(SELECTED_STATIONS):
        name = code_to_name.get(code, code)
        lat, lon = MTR_STATION_COORDS.get(code, (0.0, 0.0))
        network.add_stop(Stop(code, name, lat, lon))

    # 2. MTR segments
    print("    Building MTR segments...")
    mtr_count = 0
    for line_code, stations in LINE_ADJACENCY.items():
        for i in range(len(stations) - 1):
            a, b = stations[i], stations[i + 1]
            for src, dst in [(a, b), (b, a)]:
                fare = fares.get((src, dst), 4.9)
                time = MTR_TRAVEL_TIMES.get((src, dst), DEFAULT_ADJACENT_TIME)
                try:
                    network.add_segment(Segment(src, dst, "MTR", time, fare))
                    mtr_count += 1
                except ValueError:
                    pass
    print(f"    -> {mtr_count} MTR segments")

    # 3. Bus segments
    print("    Building bus segments...")
    bus_count = 0
    for src, dst, dur, cost in BUS_SEGMENTS:
        try:
            network.add_segment(Segment(src, dst, "Bus", dur, cost))
            bus_count += 1
        except ValueError:
            pass
    print(f"    -> {bus_count} bus segments")

    # 4. Minibus segments
    mini_count = 0
    for src, dst, dur, cost in MINIBUS_SEGMENTS:
        try:
            network.add_segment(Segment(src, dst, "Minibus", dur, cost))
            mini_count += 1
        except ValueError:
            pass
    print(f"    -> {mini_count} minibus segments")

    # 5. Walking segments
    print("    Building walking segments...")
    walk_count = 0
    for src, dst, dur in WALKING_SEGMENTS:
        try:
            network.add_segment(Segment(src, dst, "Walking", dur, 0.0))
            network.add_segment(Segment(dst, src, "Walking", dur, 0.0))
            walk_count += 2
        except ValueError:
            pass
    print(f"    -> {walk_count} walking segments")

    return network


# ================================================================
#  Main entry point
# ================================================================

def fetch_and_build_network():
    """
    Fetch real data from government APIs, combine with curated
    segments, and return a TransportNetwork.

    Returns:
        (network, output_path) tuple.
    """
    print("  [fetch_real_data] Starting data fetch...")

    code_to_name, code_to_id = fetch_mtr_station_names()
    fares = fetch_mtr_fares(code_to_id)
    network = build_network(code_to_name, fares)

    # Save to file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    save_network(network, output_path)
    print(f"  [fetch_real_data] Saved to {output_path}")
    print(f"  [fetch_real_data] Total: {len(network.stops)} stops, "
          f"{len(network.segments)} segments")

    return network, output_path


if __name__ == "__main__":
    net, path = fetch_and_build_network()
    print(f"\nDone. {len(net.stops)} stops, {len(net.segments)} segments.")
    print(f"Saved to: {path}")
