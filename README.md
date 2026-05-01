# Smart Public Transport Advisor

COMP1110 A04 Group Project - Topic B: Smart Public Transport Advisor 

By Hu Xiaobang, Lau Yat Ching Edmond, Mao Junkai, and Qin Puxun Anderson

## Project Overview

This is a text-based public transport route advisor. It models a small city transport network as stops and travel segments. A user can choose an origin, destination, and travel preference, then generate possible journeys and rank them according to the selected preference.

The default example network is based on Hong Kong's public transport. It contains 12 stops and 40 segments across MTR, bus, minibus, and walking.

The program also supports fetching real transport data from Hong Kong government open-data APIs (MTR station names and adult Octopus fares), combined with curated bus, minibus, and walking segments, to build a larger 36-stop, 122-segment network covering eight MTR lines.

## Language and Environment

- Language: Python
- Recommended version: Python 3.10 or later
- External packages: none
- Interface: command-line text menu

The project uses only the Python standard library.

## File Structure

```text
COMP1110/
  main.py                 Text-based menu and user workflows
  models.py               Stop, Segment, Journey, and TransportNetwork classes
  planner.py              Journey generation and ranking (DFS + Dijkstra)
  file_io.py              Load/save transport network files
  fetch_real_data.py      Fetch real HK data from government APIs
  data/
    hk_network.txt        Sample Hong Kong transport network (12 stops)
    hk_network_real.txt   Real-data network (36 stops, auto-generated)
    test_cases.py         Automated tests and case-study demonstrations
README.md                 Project description/instructions (you are here!)
CASE_STUDY_RESULTS.md     Detailed case study outputs and discussion
```

## How to Run

Open a terminal in the project folder, then move into the source directory:

```powershell
cd COMP1110
python main.py
```

The program loads the default Hong Kong network automatically. Use the menu to:

- list all stops
- query journeys
- show the network summary
- show all segments
- load a network from file
- generate sample data files
- export the latest query result
- fetch real HK network from government APIs

## Example Query

Example input:

```text
Origin: CEN
Destination: SHA
Preference: cheapest
```

Expected behavior:

- The program finds candidate journeys from Central to Sha Tin.
- It ranks them by lowest total cost.
- It displays the top journeys with total duration, total cost, segment count, transfer count, transport types, and step-by-step breakdown.

## Preference Modes

The program supports these ranking modes:

| Mode | Meaning |
| --- | --- |
| `fastest` | Rank by shortest total duration |
| `cheapest` | Rank by lowest total cost |
| `fewest_segments` | Rank by fewest travel legs |
| `fewest_transfers` | Rank by fewest changes between transport types |

If two journeys tie on the main preference, the ranking function uses a simple secondary value such as duration or cost.

## Network File Format

Network files use a simple CSV-like text format. Blank lines and lines starting with `#` are ignored.

```text
STOP,<stop_id>,<name>,<latitude>,<longitude>
SEGMENT,<from_id>,<to_id>,<transport_type>,<duration_min>,<cost_hkd>
```

Example:

```text
STOP,CEN,Central,22.2820,114.1588
STOP,ADM,Admiralty,22.2793,114.1654
SEGMENT,CEN,ADM,MTR,2,4.9
SEGMENT,ADM,CEN,MTR,2,4.9
```

Segments are directed. If travel should be possible in both directions, the file must include one segment for each direction.

## How Journey Generation Works

The program offers two route-finding algorithms:

### Depth-Limited DFS (default for small networks ≤ 30 stops)

- Enumerates all simple paths (no repeated stops) up to a maximum depth.
- Generates many candidate journeys for flexible post-hoc ranking.
- Simple and effective for small hand-crafted networks.

### Dijkstra + Yen's K-Shortest Paths (auto-selected for larger networks > 30 stops)

- Dijkstra's algorithm guarantees the optimal journey for the selected preference.
- Yen's algorithm extends this to find the top-k alternative journeys.
- Efficient even on larger networks (e.g., the 36-stop real-data network).

The algorithm is selected automatically based on network size, or can be forced manually via the `method` parameter.

## Real Data from Government APIs

Use menu option `9` to fetch real transport data from:

- **MTR stations and line topology:** `opendata.mtr.com.hk` (CSV)
- **MTR adult Octopus fares:** `opendata.mtr.com.hk` (CSV)

This is combined with hand-curated data for:

- Bus and minibus segments (fares and durations from official route info)
- Walking segments between nearby stations (surveyed manually)
- MTR travel times (estimated from public timetables)
- Station coordinates (public geographic data)

The resulting network covers 36 core stations across 8 MTR lines (ISL, TWL, KTL, TKL, EAL, TML, SIL, TCL) with 122 segments. It is saved to `data/hk_network_real.txt` in the same format as the sample network.

## How to Run Tests

From the `COMP1110` directory:

```bash
cd COMP1110
python data/test_cases.py
```

No `PYTHONPATH` setup is needed — the test script automatically adds the
parent directory to the import path.

The test suite covers:

- stop, segment, journey, and network model behavior
- file loading and saving
- journey generation (DFS and Dijkstra)
- journey ranking
- algorithm auto-selection by network size
- four case-study scenarios on the sample network
- case study 5 on the real-data network (walking shortcuts, multi-modal routing)

Current expected result:

```text
69 passed, 0 failed
```

## Case Studies

The test file includes five case-study demonstrations:

1. Budget commuter: Central to Sha Tin using `cheapest` (sample network).
2. Rush-hour student: Tsuen Wan to Causeway Bay using `fastest` (sample network).
3. Transfer-averse user: Tseung Kwan O to Tsim Sha Tsui using `fewest_transfers` (sample network).
4. Preference comparison: Admiralty to Kowloon Tong using all preference modes (sample network).
5. Real-data network: Walking shortcuts (TST→ETS), multi-modal routing (CEN→SHT), and sample-vs-real comparison (real network, 36 stops).

For each case, the program generates candidate journeys, ranks them, and prints the best route with time, cost, segment count, and route steps.

Detailed case-study outputs and discussion are recorded in `CASE_STUDY_RESULTS.md`.

## Input Validation and Error Handling

The program handles common invalid input cases:

- empty menu choices
- unknown stop IDs or names
- same origin and destination
- invalid preference modes
- invalid result counts
- missing, empty, or malformed network files
- disconnected origin/destination pairs

## Limitations

This is a simplified academic project, not a real transport app.

- No real-time arrival or delay data.
- No live map display.
- No GPS or location detection.
- No database storage.
- Student, child, and elderly travel fares not accounted for (only adult).
- MTR fares are per-segment (from API OD pairs between adjacent selected stations); multi-segment MTR journeys may slightly differ from the actual end-to-end Octopus fare.
- Bus/minibus fares and durations are curated estimates, not live data.
- Walking links only exist where explicitly listed.
- DFS may miss better routes in larger networks (Dijkstra addresses this).

## Future Improvements

Possible improvements include:

- Expanding the real-data network to cover more stations and bus routes
- Adding real-time ETA data from MTR and KMB APIs
- Supporting student, child, and elderly concession fares
- Adding accessibility preferences (e.g., barrier-free routes)
- Estimating walking segments automatically from station coordinates
- Supporting more detailed transfer penalties (waiting time, walking distance)
- Adding a graphical or web-based interface
