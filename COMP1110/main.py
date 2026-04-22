"""
main.py - Smart Public Transport Advisor
Text-based menu, input validation, display, and integration.

Author: Member 4
"""

import os
import sys
from models import TransportNetwork
from file_io import load_network, create_default_network, generate_sample_files, save_network
from planner import find_journeys, rank_journeys, VALID_PREFERENCES


# ================================================================
#  Constants
# ================================================================

VERSION = "1.0"
MAX_DISPLAY = 5          # Max journeys to display per query
LOG_DIR = "output"       # Directory for exported results


# ================================================================
#  Display helpers
# ================================================================

def display_banner():
    print()
    print("=" * 58)
    print(f"   Smart Public Transport Advisor  v{VERSION}")
    print("   COMP1110 Group Project")
    print("=" * 58)


def display_menu():
    print()
    print("-" * 42)
    print("  Main Menu")
    print("-" * 42)
    print("  1. List all stops")
    print("  2. Query journeys")
    print("  3. Show network summary")
    print("  4. Show all segments")
    print("  5. Load network from file")
    print("  6. Generate sample data files")
    print("  7. Export last query results to file")
    print("  8. Help")
    print("  0. Exit")
    print("-" * 42)


def display_stops(network):
    if network.is_empty():
        print("\n  [!] No stops loaded in the network.")
        return
    print()
    header = f"  {'ID':<8} {'Name':<22} {'Lat':<10} {'Lon':<10} {'Outgoing':<8}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for stop in sorted(network.stops.values(), key=lambda s: s.stop_id):
        out_count = len(network.get_outgoing(stop.stop_id))
        print(f"  {stop.stop_id:<8} {stop.name:<22} "
              f"{stop.latitude:<10.4f} {stop.longitude:<10.4f} {out_count:<8}")
    print(f"\n  Total: {len(network.stops)} stop(s)")


def display_segments(network):
    if not network.segments:
        print("\n  [!] No segments in the network.")
        return
    print()
    header = (f"  {'From':<18} {'To':<18} {'Type':<10} "
              f"{'Dur(min)':<10} {'Cost($)':<10}")
    print(header)
    print("  " + "-" * (len(header) - 2))
    for seg in network.segments:
        fn = network.get_stop(seg.from_stop_id)
        tn = network.get_stop(seg.to_stop_id)
        fn_name = fn.name if fn else seg.from_stop_id
        tn_name = tn.name if tn else seg.to_stop_id
        print(f"  {fn_name:<18} {tn_name:<18} {seg.transport_type:<10} "
              f"{seg.duration:<10.1f} {seg.cost:<10.1f}")
    print(f"\n  Total: {len(network.segments)} segment(s)")


def format_journey(journey, network, rank):
    """Return a formatted string for one journey (for display and export)."""
    lines = []
    lines.append(f"  ┌─── Journey #{rank} {'─' * 34}")
    lines.append(f"  │  Total duration:  {journey.total_duration:.1f} min")
    lines.append(f"  │  Total cost:      ${journey.total_cost:.1f} HKD")
    lines.append(f"  │  Segments:        {journey.num_segments}")
    lines.append(f"  │  Transfers:       {journey.num_transfers}")
    lines.append(f"  │  Transport used:  {', '.join(journey.transport_types_used)}")
    lines.append(f"  │")
    lines.append(f"  │  Step-by-step breakdown:")
    for i, seg in enumerate(journey.segments, 1):
        f_stop = network.get_stop(seg.from_stop_id)
        t_stop = network.get_stop(seg.to_stop_id)
        f_name = f_stop.name if f_stop else seg.from_stop_id
        t_name = t_stop.name if t_stop else seg.to_stop_id
        lines.append(
            f"  │   {i}. [{seg.transport_type:<8}] "
            f"{f_name} → {t_name}  "
            f"({seg.duration:.0f} min, ${seg.cost:.1f})"
        )
    lines.append(f"  └{'─' * 50}")
    return "\n".join(lines)


def display_journey(journey, network, rank):
    print(format_journey(journey, network, rank))


def display_help():
    print("""
  ── Help ──────────────────────────────────────────────

  This program finds public transport routes between
  stops in a pre-defined transport network.

  QUICK START:
    1) A default HK network is loaded on startup.
    2) Use [1] to see available stops and their IDs.
    3) Use [2] to search for journeys between two stops.
       Enter stop IDs or names, pick a preference mode,
       and view ranked results with full breakdowns.

  PREFERENCE MODES:
    fastest          - Minimize total travel time
    cheapest         - Minimize total fare
    fewest_segments  - Minimize number of ride legs
    fewest_transfers - Minimize mode changes

  LOADING CUSTOM NETWORKS:
    Use [5] and provide a file path, or type 'default'.
    File format: STOP,<id>,<name>,<lat>,<lon>
                 SEGMENT,<from>,<to>,<type>,<dur>,<cost>

  EXPORTING RESULTS:
    Use [7] to save the last query output to a text file.

  WHAT THIS PROGRAM DOES NOT DO:
    • No real-time or live data from the internet
    • No graphical map display
    • No GPS or location services
    • No database storage
    • Routes are found by depth-limited search, NOT
      guaranteed to be globally optimal
  ────────────────────────────────────────────────────────
""")


# ================================================================
#  Input validation
# ================================================================

def validate_stop(network, prompt):
    """
    Prompt user for a stop by ID or name.
    Supports: exact ID, exact name (case-insensitive), partial search.
    Returns stop_id string or None if cancelled.
    """
    while True:
        user_input = input(prompt).strip()

        if not user_input:
            print("  [!] Input cannot be empty. Please enter a stop ID or name.")
            if not _ask_retry():
                return None
            continue

        # 1. Exact ID match
        if network.has_stop(user_input):
            stop = network.get_stop(user_input)
            print(f"  → {stop.name} [{stop.stop_id}]")
            return user_input

        # 2. Exact name match (case-insensitive)
        stop = network.find_stop_by_name(user_input)
        if stop:
            print(f"  → {stop.name} [{stop.stop_id}]")
            return stop.stop_id

        # 3. Partial search
        matches = network.search_stops(user_input)
        if len(matches) == 1:
            print(f"  → {matches[0].name} [{matches[0].stop_id}]")
            return matches[0].stop_id
        elif len(matches) > 1:
            print(f"  [!] Multiple matches for '{user_input}':")
            for m in sorted(matches, key=lambda s: s.stop_id):
                print(f"      {m.stop_id:>6} - {m.name}")
            print("  Please enter a more specific ID or name.")
            if not _ask_retry():
                return None
            continue

        # 4. No match
        print(f"  [!] Stop '{user_input}' not found in the network.")
        print("      Tip: Use menu option [1] to list all available stops.")
        if not _ask_retry():
            return None


def validate_preference():
    """
    Prompt user to select a preference mode.
    Accepts number (1-4) or name string.
    Returns preference string or None if cancelled.
    """
    while True:
        print("\n  Available preference modes:")
        for i, pref in enumerate(VALID_PREFERENCES, 1):
            desc = PREFERENCE_DESCRIPTIONS.get(pref, "")
            print(f"    {i}. {pref:<20} — {desc}")

        user_input = input("  Select preference (number or name): ").strip().lower()

        if not user_input:
            print("  [!] Input cannot be empty.")
            if not _ask_retry():
                return None
            continue

        # Numeric
        try:
            idx = int(user_input) - 1
            if 0 <= idx < len(VALID_PREFERENCES):
                chosen = VALID_PREFERENCES[idx]
                print(f"  → Preference: {chosen}")
                return chosen
            else:
                print(f"  [!] Number out of range. Enter 1 to {len(VALID_PREFERENCES)}.")
                if not _ask_retry():
                    return None
                continue
        except ValueError:
            pass

        # Exact name
        if user_input in VALID_PREFERENCES:
            print(f"  → Preference: {user_input}")
            return user_input

        # Partial
        partials = [p for p in VALID_PREFERENCES if user_input in p]
        if len(partials) == 1:
            print(f"  → Preference: {partials[0]}")
            return partials[0]

        print(f"  [!] Invalid preference '{user_input}'.")
        if not _ask_retry():
            return None


def validate_positive_int(prompt, default=None):
    """Prompt for a positive integer. Returns int or default."""
    while True:
        hint = f" (default {default})" if default else ""
        user_input = input(f"{prompt}{hint}: ").strip()
        if not user_input and default is not None:
            return default
        try:
            val = int(user_input)
            if val > 0:
                return val
            print("  [!] Must be a positive integer.")
        except ValueError:
            print("  [!] Invalid number.")
        if not _ask_retry():
            return default


def _ask_retry():
    """Ask user if they want to try again."""
    ans = input("  Try again? (y/n) [y]: ").strip().lower()
    return ans in ("y", "yes", "")


# ================================================================
#  Core workflows
# ================================================================

# Global: stores last query result for export
_last_query_output = None


def query_journeys_flow(network):
    """Full workflow: origin → destination → preference → search → display."""
    global _last_query_output

    if network.is_empty():
        print("\n  [!] No network loaded. Please load one first (option 5).")
        return

    print("\n  ── Query Journeys ──")

    # 1. Origin
    origin_id = validate_stop(network, "  Enter origin (ID or name): ")
    if origin_id is None:
        print("  Query cancelled.")
        return

    # 2. Destination
    dest_id = validate_stop(network, "  Enter destination (ID or name): ")
    if dest_id is None:
        print("  Query cancelled.")
        return

    # 3. Same origin / destination
    if origin_id == dest_id:
        print("  [!] Origin and destination are the same stop. No journey needed.")
        return

    # 4. Connectivity check
    if not network.is_reachable(origin_id, dest_id):
        o_name = network.get_stop(origin_id).name
        d_name = network.get_stop(dest_id).name
        print(f"\n  [!] {d_name} is NOT reachable from {o_name} in this network.")
        print("      The network may be disconnected or only have one-way segments.")
        return

    # 5. Preference
    preference = validate_preference()
    if preference is None:
        print("  Query cancelled.")
        return

    # 6. Optional: max results
    max_show = validate_positive_int(
        "  How many results to display?", default=MAX_DISPLAY
    )

    # 7. Search
    o_name = network.get_stop(origin_id).name
    d_name = network.get_stop(dest_id).name
    print(f"\n  Searching: {o_name} → {d_name}  [mode: {preference}]")
    print("  Please wait...")

    try:
        journeys = find_journeys(network, origin_id, dest_id)
    except ValueError as e:
        print(f"  [!] Error during search: {e}")
        return

    if not journeys:
        print(f"\n  [!] No routes found from {o_name} to {d_name}.")
        return

    ranked = rank_journeys(journeys, preference)

    # 8. Display
    show_n = min(max_show, len(ranked))
    print(f"\n  Found {len(ranked)} route(s). Showing top {show_n}:\n")

    output_lines = []
    output_lines.append(f"Query: {o_name} [{origin_id}] → {d_name} [{dest_id}]")
    output_lines.append(f"Preference: {preference}")
    output_lines.append(f"Total routes found: {len(ranked)}, showing top {show_n}")
    output_lines.append("")

    for i in range(show_n):
        j_text = format_journey(ranked[i], network, i + 1)
        print(j_text)
        output_lines.append(j_text)

    # Comparison summary table
    print(f"\n  {'─' * 58}")
    print(f"  {'#':<4} {'Duration':<12} {'Cost':<10} {'Seg':<6} {'Xfer':<6} {'Types'}")
    print(f"  {'─' * 58}")
    for i in range(show_n):
        j = ranked[i]
        types_str = ",".join(j.transport_types_used)
        row = (f"  {i+1:<4} {j.total_duration:<12.1f} "
               f"${j.total_cost:<9.1f} {j.num_segments:<6} "
               f"{j.num_transfers:<6} {types_str}")
        print(row)
        output_lines.append(row)
    print(f"  {'─' * 58}")

    _last_query_output = "\n".join(output_lines)


def load_network_flow(network):
    """Workflow to load network from file or use default."""
    print("\n  ── Load Network ──")
    print("  Enter file path, or 'default' for built-in HK network.")
    print("  Enter 'list' to see files in data/ directory.")

    filepath = input("  File path: ").strip()

    if not filepath:
        print("  [!] Empty path. Operation cancelled.")
        return network

    if filepath.lower() == "list":
        _list_data_files()
        filepath = input("  File path: ").strip()
        if not filepath:
            return network

    if filepath.lower() == "default":
        new_net = create_default_network()
        print(f"  ✓ Default network loaded: {len(new_net.stops)} stops, "
              f"{len(new_net.segments)} segments.")
        return new_net

    try:
        new_net = load_network(filepath)
        if new_net.is_empty():
            print("  [!] File loaded but network is empty (no valid stops/segments).")
            return network
        print(f"  ✓ Network loaded: {len(new_net.stops)} stops, "
              f"{len(new_net.segments)} segments.")

        # Minimum size warning
        if len(new_net.stops) < 10 or len(new_net.segments) < 20:
            print(f"  [!] Warning: Network is below recommended minimum "
                  f"(10 stops, 20 segments).")
            print(f"      Current: {len(new_net.stops)} stops, "
                  f"{len(new_net.segments)} segments.")

        return new_net

    except FileNotFoundError as e:
        print(f"  [!] {e}")
    except ValueError as e:
        print(f"  [!] {e}")
    except Exception as e:
        print(f"  [!] Unexpected error: {e}")

    return network


def export_results_flow():
    """Export last query results to a text file."""
    global _last_query_output
    if _last_query_output is None:
        print("\n  [!] No query results to export. Run a query first (option 2).")
        return

    os.makedirs(LOG_DIR, exist_ok=True)

    # Auto-generate filename
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"query_{timestamp}.txt"
    filename = input(f"  Output filename [{default_name}]: ").strip()
    if not filename:
        filename = default_name

    filepath = os.path.join(LOG_DIR, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Smart Public Transport Advisor - Query Results\n")
            f.write(f"Generated: {datetime.datetime.now()}\n")
            f.write("=" * 60 + "\n\n")
            f.write(_last_query_output)
            f.write("\n")
        print(f"  ✓ Results exported to: {filepath}")
    except Exception as e:
        print(f"  [!] Failed to export: {e}")


def _list_data_files():
    """List files in the data/ directory."""
    data_dir = "data"
    if not os.path.isdir(data_dir):
        print(f"  [!] Directory '{data_dir}' not found.")
        return
    files = [f for f in os.listdir(data_dir) if f.endswith(".txt")]
    if not files:
        print(f"  [!] No .txt files in '{data_dir}/'.")
    else:
        print(f"\n  Files in {data_dir}/:")
        for fn in sorted(files):
            size = os.path.getsize(os.path.join(data_dir, fn))
            print(f"    {fn:<30} ({size} bytes)")
    print()


# ================================================================
#  Main loop
# ================================================================

def main():
    display_banner()

    # Load default network on startup
    network = create_default_network()
    print(f"\n  Default HK network loaded: {len(network.stops)} stops, "
          f"{len(network.segments)} segments.")
    print("  Type '8' for help or '0' to exit.")

    while True:
        display_menu()
        choice = input("  Your choice: ").strip()

        if choice == "1":
            display_stops(network)

        elif choice == "2":
            query_journeys_flow(network)

        elif choice == "3":
            print(f"\n{network.summary_string()}")

        elif choice == "4":
            display_segments(network)

        elif choice == "5":
            network = load_network_flow(network)

        elif choice == "6":
            print("\n  Generating sample data files...")
            generate_all_sample_files()
            print("  Done.")

        elif choice == "7":
            export_results_flow()

        elif choice == "8":
            display_help()

        elif choice == "0":
            print("\n  Goodbye! Thank you for using Smart Public Transport Advisor.\n")
            break

        else:
            print(f"  [!] Invalid choice '{choice}'. Please enter 0-8.")


if __name__ == "__main__":
    main()