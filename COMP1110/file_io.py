"""
file_io.py - File I/O for loading and saving transport networks.

File format (plain text, CSV-like):
  Lines starting with '#' are comments and are ignored.
  Blank lines are ignored.

  STOP,<stop_id>,<name>,<latitude>,<longitude>
  SEGMENT,<from_id>,<to_id>,<transport_type>,<duration_min>,<cost_hkd>
"""

import os
from models import Stop, Segment, TransportNetwork


def load_network(filepath):
    """
    Load a TransportNetwork from a text file.
    
    Raises:
        FileNotFoundError: if file does not exist.
        ValueError: if file is empty or has no valid data.
    
    Returns:
        TransportNetwork object.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: '{filepath}'")

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Check for empty file
    data_lines = [ln.strip() for ln in lines
                  if ln.strip() and not ln.strip().startswith("#")]
    if not data_lines:
        raise ValueError(f"File is empty or contains no data: '{filepath}'")

    network = TransportNetwork()
    warnings = []

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split(",")]
        record_type = parts[0].upper()

        try:
            if record_type == "STOP":
                if len(parts) != 5:
                    warnings.append(f"Line {line_num}: STOP expects 5 fields, got {len(parts)}")
                    continue
                sid, name = parts[1], parts[2]
                lat, lon = float(parts[3]), float(parts[4])
                network.add_stop(Stop(sid, name, lat, lon))

            elif record_type == "SEGMENT":
                if len(parts) != 6:
                    warnings.append(f"Line {line_num}: SEGMENT expects 6 fields, got {len(parts)}")
                    continue
                from_id, to_id, transport = parts[1], parts[2], parts[3]
                duration, cost = float(parts[4]), float(parts[5])
                if duration < 0:
                    warnings.append(f"Line {line_num}: Negative duration ignored")
                    continue
                if cost < 0:
                    warnings.append(f"Line {line_num}: Negative cost ignored")
                    continue
                network.add_segment(Segment(from_id, to_id, transport, duration, cost))

            else:
                warnings.append(f"Line {line_num}: Unknown record type '{parts[0]}'")

        except ValueError as e:
            warnings.append(f"Line {line_num}: {e}")

    # Print any warnings
    if warnings:
        print(f"  [!] {len(warnings)} warning(s) during loading:")
        for w in warnings:
            print(f"      {w}")

    return network


def save_network(network, filepath):
    """Save a TransportNetwork to a text file."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# Smart Public Transport Advisor - Network Data\n")
        f.write("# STOP,<id>,<name>,<latitude>,<longitude>\n")
        f.write("# SEGMENT,<from>,<to>,<type>,<duration_min>,<cost_hkd>\n\n")

        f.write("# === Stops ===\n")
        for stop in network.stops.values():
            f.write(f"STOP,{stop.stop_id},{stop.name},{stop.latitude},{stop.longitude}\n")

        f.write("\n# === Segments ===\n")
        for seg in network.segments:
            f.write(f"SEGMENT,{seg.from_stop_id},{seg.to_stop_id},"
                    f"{seg.transport_type},{seg.duration},{seg.cost}\n")


def create_default_network():
    """
    Build a default Hong Kong transport network.
    12 stops, 40 segments covering MTR, Bus, Minibus, Walking.
    """
    network = TransportNetwork()

    # --- 12 Stops ---
    stop_data = [
        ("CEN", "Central",         22.2820, 114.1588),
        ("ADM", "Admiralty",        22.2793, 114.1654),
        ("WCH", "Wan Chai",         22.2783, 114.1747),
        ("CWB", "Causeway Bay",     22.2800, 114.1840),
        ("NOP", "North Point",      22.2914, 114.2004),
        ("TST", "Tsim Sha Tsui",    22.2974, 114.1722),
        ("YMT", "Yau Ma Tei",       22.3133, 114.1708),
        ("MKK", "Mong Kok",         22.3193, 114.1694),
        ("KOT", "Kowloon Tong",     22.3372, 114.1760),
        ("SHA", "Sha Tin",           22.3825, 114.1878),
        ("TKO", "Tseung Kwan O",    22.3045, 114.2599),
        ("TWN", "Tsuen Wan",         22.3684, 114.1099),
    ]
    for sid, name, lat, lon in stop_data:
        network.add_stop(Stop(sid, name, lat, lon))

    # --- 40 Segments ---
    # (from, to, type, duration_min, cost_hkd)
    segment_data = [
        # MTR Island Line
        ("CEN", "ADM", "MTR",  2,  5.2),
        ("ADM", "CEN", "MTR",  2,  5.2),
        ("ADM", "WCH", "MTR",  2,  5.2),
        ("WCH", "ADM", "MTR",  2,  5.2),
        ("WCH", "CWB", "MTR",  2,  5.2),
        ("CWB", "WCH", "MTR",  2,  5.2),
        ("CWB", "NOP", "MTR",  3,  5.8),
        ("NOP", "CWB", "MTR",  3,  5.8),
        # MTR Cross-harbour
        ("ADM", "TST", "MTR",  4, 10.5),
        ("TST", "ADM", "MTR",  4, 10.5),
        # MTR Tsuen Wan Line (Kowloon side)
        ("TST", "YMT", "MTR",  2,  5.2),
        ("YMT", "TST", "MTR",  2,  5.2),
        ("YMT", "MKK", "MTR",  2,  5.2),
        ("MKK", "YMT", "MTR",  2,  5.2),
        # MTR Kwun Tong / East Rail connections
        ("MKK", "KOT", "MTR",  6,  8.5),
        ("KOT", "MKK", "MTR",  6,  8.5),
        ("KOT", "SHA", "MTR", 10, 12.0),
        ("SHA", "KOT", "MTR", 10, 12.0),
        # MTR Tseung Kwan O Line
        ("NOP", "TKO", "MTR", 15, 10.5),
        ("TKO", "NOP", "MTR", 15, 10.5),
        # MTR Tsuen Wan extension
        ("MKK", "TWN", "MTR", 15, 12.0),
        ("TWN", "MKK", "MTR", 15, 12.0),

        # Bus routes
        ("CEN", "CWB", "Bus",  15,  4.2),
        ("CWB", "CEN", "Bus",  15,  4.2),
        ("CEN", "TST", "Bus",  20,  6.8),   # Cross-harbour bus
        ("TST", "CEN", "Bus",  20,  6.8),
        ("MKK", "SHA", "Bus",  25,  8.5),
        ("SHA", "MKK", "Bus",  25,  8.5),
        ("TST", "TWN", "Bus",  30,  9.0),
        ("TWN", "TST", "Bus",  30,  9.0),
        ("CWB", "TKO", "Bus",  35,  9.8),
        ("TKO", "CWB", "Bus",  35,  9.8),

        # Minibus
        ("CEN", "WCH", "Minibus", 10, 3.5),
        ("WCH", "CEN", "Minibus", 10, 3.5),
        ("TST", "MKK", "Minibus",  8, 4.0),
        ("MKK", "TST", "Minibus",  8, 4.0),

        # Walking (free)
        ("ADM", "WCH", "Walking", 15, 0.0),
        ("WCH", "ADM", "Walking", 15, 0.0),
        ("TST", "YMT", "Walking", 12, 0.0),
        ("YMT", "TST", "Walking", 12, 0.0),
    ]
    for from_id, to_id, t_type, dur, cost in segment_data:
        network.add_segment(Segment(from_id, to_id, t_type, dur, cost))

    return network


def generate_sample_files():
    """Generate sample network data files in the data/ directory."""
    # 1. Default HK network
    net = create_default_network()
    save_network(net, os.path.join("data", "hk_network.txt"))
    print("Generated: data/hk_network.txt")

    # 2. Small test network (for quick testing)
    small = TransportNetwork()
    for sid, name in [("A", "Stop A"), ("B", "Stop B"), ("C", "Stop C"),
                      ("D", "Stop D"), ("E", "Stop E")]:
        small.add_stop(Stop(sid, name))

    small_segs = [
        ("A", "B", "MTR",  5,  6.0),
        ("B", "A", "MTR",  5,  6.0),
        ("B", "C", "MTR",  3,  4.0),
        ("C", "B", "MTR",  3,  4.0),
        ("A", "C", "Bus", 12,  3.0),
        ("C", "A", "Bus", 12,  3.0),
        ("C", "D", "Bus",  8,  5.0),
        ("D", "C", "Bus",  8,  5.0),
        ("B", "D", "Walking", 15, 0.0),
        ("D", "B", "Walking", 15, 0.0),
        ("D", "E", "MTR",  4,  5.0),
        ("E", "D", "MTR",  4,  5.0),
        ("A", "D", "Bus",  20, 4.5),
        ("D", "A", "Bus",  20, 4.5),
    ]
    for f, t, tp, dur, cost in small_segs:
        small.add_segment(Segment(f, t, tp, dur, cost))

    save_network(small, os.path.join("data", "test_small.txt"))
    print("Generated: data/test_small.txt")


# Allow direct execution to generate files
if __name__ == "__main__":
    generate_sample_files()