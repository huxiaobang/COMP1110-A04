"""
main.py - Smart Public Transport Advisor.
Text-based menu, input validation, display, and integration.
"""

import datetime
import os

from file_io import create_default_network, generate_sample_files, load_network
from planner import VALID_PREFERENCES, find_journeys, rank_journeys


VERSION = "1.0"
MAX_DISPLAY = 5
LOG_DIR = "output"
BOM_PREFIXES = ("\ufeff", "\u00ef\u00bb\u00bf", "\u9518\udcbf")

PREFERENCE_DESCRIPTIONS = {
    "fastest": "Minimize total travel time",
    "cheapest": "Minimize total fare",
    "fewest_segments": "Minimize the number of journey legs",
    "fewest_transfers": "Minimize changes between transport types",
}

_last_query_output = None


def read_input(prompt, eof_default=""):
    """Read user input and normalize common console artifacts."""
    try:
        text = input(prompt).strip()
        for prefix in BOM_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        return text
    except EOFError:
        print()
        return eof_default


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
        print(
            f"  {stop.stop_id:<8} {stop.name:<22} "
            f"{stop.latitude:<10.4f} {stop.longitude:<10.4f} {out_count:<8}"
        )
    print(f"\n  Total: {len(network.stops)} stop(s)")


def display_segments(network):
    if not network.segments:
        print("\n  [!] No segments in the network.")
        return

    print()
    header = (
        f"  {'From':<18} {'To':<18} {'Type':<10} "
        f"{'Dur(min)':<10} {'Cost($)':<10}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for segment in network.segments:
        from_stop = network.get_stop(segment.from_stop_id)
        to_stop = network.get_stop(segment.to_stop_id)
        from_name = from_stop.name if from_stop else segment.from_stop_id
        to_name = to_stop.name if to_stop else segment.to_stop_id
        print(
            f"  {from_name:<18} {to_name:<18} {segment.transport_type:<10} "
            f"{segment.duration:<10.1f} {segment.cost:<10.1f}"
        )
    print(f"\n  Total: {len(network.segments)} segment(s)")


def format_journey(journey, network, rank):
    """Return a formatted string for one journey."""
    lines = [
        f"  Journey #{rank}",
        f"  {'-' * 50}",
        f"  Total duration:  {journey.total_duration:.1f} min",
        f"  Total cost:      ${journey.total_cost:.1f} HKD",
        f"  Segments:        {journey.num_segments}",
        f"  Transfers:       {journey.num_transfers}",
        f"  Transport used:  {', '.join(journey.transport_types_used)}",
        "  Step-by-step breakdown:",
    ]

    for i, segment in enumerate(journey.segments, 1):
        from_stop = network.get_stop(segment.from_stop_id)
        to_stop = network.get_stop(segment.to_stop_id)
        from_name = from_stop.name if from_stop else segment.from_stop_id
        to_name = to_stop.name if to_stop else segment.to_stop_id
        lines.append(
            f"    {i}. [{segment.transport_type:<8}] "
            f"{from_name} -> {to_name} "
            f"({segment.duration:.0f} min, ${segment.cost:.1f})"
        )
    return "\n".join(lines)


def display_help():
    print(
        """
  Help
  --------------------------------------------------
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
    - No real-time or live data from the internet
    - No graphical map display
    - No GPS or location services
    - No database storage
    - Routes are found by depth-limited search and are not
      guaranteed to be globally optimal.
  --------------------------------------------------
"""
    )


def validate_stop(network, prompt):
    """
    Prompt user for a stop by ID or name.
    Supports exact ID, exact name, and partial search.
    """
    while True:
        user_input = read_input(prompt)
        if not user_input:
            print("  [!] Input cannot be empty. Please enter a stop ID or name.")
            if not _ask_retry():
                return None
            continue

        if network.has_stop(user_input):
            stop = network.get_stop(user_input)
            print(f"  -> {stop.name} [{stop.stop_id}]")
            return user_input

        upper_stop_id = user_input.upper()
        if upper_stop_id != user_input and network.has_stop(upper_stop_id):
            stop = network.get_stop(upper_stop_id)
            print(f"  -> {stop.name} [{stop.stop_id}]")
            return upper_stop_id

        stop = network.find_stop_by_name(user_input)
        if stop:
            print(f"  -> {stop.name} [{stop.stop_id}]")
            return stop.stop_id

        matches = network.search_stops(user_input)
        if len(matches) == 1:
            print(f"  -> {matches[0].name} [{matches[0].stop_id}]")
            return matches[0].stop_id
        if len(matches) > 1:
            print(f"  [!] Multiple matches for '{user_input}':")
            for match in sorted(matches, key=lambda s: s.stop_id):
                print(f"      {match.stop_id:>6} - {match.name}")
            print("  Please enter a more specific ID or name.")
            if not _ask_retry():
                return None
            continue

        print(f"  [!] Stop '{user_input}' not found in the network.")
        print("      Tip: Use menu option [1] to list all available stops.")
        if not _ask_retry():
            return None


def validate_preference():
    """Prompt user to select a preference mode."""
    while True:
        print("\n  Available preference modes:")
        for i, preference in enumerate(VALID_PREFERENCES, 1):
            desc = PREFERENCE_DESCRIPTIONS.get(preference, "")
            print(f"    {i}. {preference:<20} - {desc}")

        user_input = read_input("  Select preference (number or name): ").lower()
        if not user_input:
            print("  [!] Input cannot be empty.")
            if not _ask_retry():
                return None
            continue

        try:
            idx = int(user_input) - 1
            if 0 <= idx < len(VALID_PREFERENCES):
                chosen = VALID_PREFERENCES[idx]
                print(f"  -> Preference: {chosen}")
                return chosen
            print(f"  [!] Number out of range. Enter 1 to {len(VALID_PREFERENCES)}.")
            if not _ask_retry():
                return None
            continue
        except ValueError:
            pass

        if user_input in VALID_PREFERENCES:
            print(f"  -> Preference: {user_input}")
            return user_input

        partials = [pref for pref in VALID_PREFERENCES if user_input in pref]
        if len(partials) == 1:
            print(f"  -> Preference: {partials[0]}")
            return partials[0]

        print(f"  [!] Invalid preference '{user_input}'.")
        if not _ask_retry():
            return None


def validate_positive_int(prompt, default=None):
    """Prompt for a positive integer."""
    while True:
        hint = f" (default {default})" if default else ""
        user_input = read_input(f"{prompt}{hint}: ")
        if not user_input and default is not None:
            return default

        try:
            value = int(user_input)
            if value > 0:
                return value
            print("  [!] Must be a positive integer.")
        except ValueError:
            print("  [!] Invalid number.")

        if not _ask_retry():
            return default


def _ask_retry():
    answer = read_input("  Try again? (y/n) [y]: ").lower()
    return answer in ("", "y", "yes")


def query_journeys_flow(network):
    """Run the full journey query workflow."""
    global _last_query_output

    if network.is_empty():
        print("\n  [!] No network loaded. Please load one first (option 5).")
        return

    print("\n  Query Journeys")

    origin_id = validate_stop(network, "  Enter origin (ID or name): ")
    if origin_id is None:
        print("  Query cancelled.")
        return

    destination_id = validate_stop(network, "  Enter destination (ID or name): ")
    if destination_id is None:
        print("  Query cancelled.")
        return

    if origin_id == destination_id:
        print("  [!] Origin and destination are the same stop. No journey needed.")
        return

    if not network.is_reachable(origin_id, destination_id):
        origin_name = network.get_stop(origin_id).name
        destination_name = network.get_stop(destination_id).name
        print(f"\n  [!] {destination_name} is not reachable from {origin_name}.")
        print("      The network may be disconnected or only have one-way segments.")
        return

    preference = validate_preference()
    if preference is None:
        print("  Query cancelled.")
        return

    max_show = validate_positive_int(
        "  How many results to display?", default=MAX_DISPLAY
    )

    origin_name = network.get_stop(origin_id).name
    destination_name = network.get_stop(destination_id).name
    print(f"\n  Searching: {origin_name} -> {destination_name} [mode: {preference}]")
    print("  Please wait...")

    journeys = find_journeys(network, origin_id, destination_id)
    if not journeys:
        print(f"\n  [!] No routes found from {origin_name} to {destination_name}.")
        return

    ranked = rank_journeys(journeys, preference)
    show_n = min(max_show, len(ranked))
    print(f"\n  Found {len(ranked)} route(s). Showing top {show_n}:\n")

    output_lines = [
        f"Query: {origin_name} [{origin_id}] -> {destination_name} [{destination_id}]",
        f"Preference: {preference}",
        f"Total routes found: {len(ranked)}, showing top {show_n}",
        "",
    ]

    for i in range(show_n):
        journey_text = format_journey(ranked[i], network, i + 1)
        print(journey_text)
        print()
        output_lines.append(journey_text)
        output_lines.append("")

    table_lines = _format_journey_summary_table(ranked[:show_n])
    print(table_lines)
    output_lines.append(table_lines)

    _last_query_output = "\n".join(output_lines)


def _format_journey_summary_table(journeys):
    lines = [
        "  " + "-" * 58,
        f"  {'#':<4} {'Duration':<12} {'Cost':<10} {'Seg':<6} {'Xfer':<6} {'Types'}",
        "  " + "-" * 58,
    ]
    for i, journey in enumerate(journeys, 1):
        types = ",".join(journey.transport_types_used)
        lines.append(
            f"  {i:<4} {journey.total_duration:<12.1f} "
            f"${journey.total_cost:<9.1f} {journey.num_segments:<6} "
            f"{journey.num_transfers:<6} {types}"
        )
    lines.append("  " + "-" * 58)
    return "\n".join(lines)


def load_network_flow(network):
    """Load a network from file or restore the default network."""
    print("\n  Load Network")
    print("  Enter file path, or 'default' for built-in HK network.")
    print("  Enter 'list' to see files in data/ directory.")

    filepath = read_input("  File path: ")
    if not filepath:
        print("  [!] Empty path. Operation cancelled.")
        return network

    if filepath.lower() == "list":
        _list_data_files()
        filepath = read_input("  File path: ")
        if not filepath:
            print("  [!] Empty path. Operation cancelled.")
            return network

    if filepath.lower() == "default":
        new_network = create_default_network()
        print(
            f"  [OK] Default network loaded: {len(new_network.stops)} stops, "
            f"{len(new_network.segments)} segments."
        )
        return new_network

    try:
        new_network = load_network(filepath)
        if new_network.is_empty():
            print("  [!] File loaded but network is empty.")
            return network

        print(
            f"  [OK] Network loaded: {len(new_network.stops)} stops, "
            f"{len(new_network.segments)} segments."
        )
        if len(new_network.stops) < 10 or len(new_network.segments) < 20:
            print("  [!] Warning: network is below the recommended minimum.")
            print(
                f"      Current: {len(new_network.stops)} stops, "
                f"{len(new_network.segments)} segments."
            )
        return new_network
    except FileNotFoundError as exc:
        print(f"  [!] {exc}")
    except ValueError as exc:
        print(f"  [!] {exc}")
    except Exception as exc:
        print(f"  [!] Unexpected error: {exc}")

    return network


def export_results_flow():
    """Export last query results to a text file."""
    global _last_query_output

    if _last_query_output is None:
        print("\n  [!] No query results to export. Run a query first (option 2).")
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"query_{timestamp}.txt"
    filename = read_input(f"  Output filename [{default_name}]: ")
    if not filename:
        filename = default_name

    filepath = os.path.join(LOG_DIR, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            file.write("Smart Public Transport Advisor - Query Results\n")
            file.write(f"Generated: {datetime.datetime.now()}\n")
            file.write("=" * 60 + "\n\n")
            file.write(_last_query_output)
            file.write("\n")
        print(f"  [OK] Results exported to: {filepath}")
    except Exception as exc:
        print(f"  [!] Failed to export: {exc}")


def _list_data_files():
    """List network text files in the data directory."""
    data_dir = "data"
    if not os.path.isdir(data_dir):
        print(f"  [!] Directory '{data_dir}' not found.")
        return

    files = [name for name in os.listdir(data_dir) if name.endswith(".txt")]
    if not files:
        print(f"  [!] No .txt files in '{data_dir}/'.")
        return

    print(f"\n  Files in {data_dir}/:")
    for filename in sorted(files):
        size = os.path.getsize(os.path.join(data_dir, filename))
        print(f"    {filename:<30} ({size} bytes)")
    print()


def main():
    display_banner()

    network = create_default_network()
    print(
        f"\n  Default HK network loaded: {len(network.stops)} stops, "
        f"{len(network.segments)} segments."
    )
    print("  Type '8' for help or '0' to exit.")

    while True:
        display_menu()
        choice = read_input("  Your choice: ", eof_default="0")

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
            generate_sample_files()
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
