# Smart Public Transport Advisor

COMP1110 A04 Group Project - Topic B: Smart Public Transport Advisor 

By Hu Xiaobang, Lau Yat Ching Edmond, Mao Junkai, and Qin Puxun Anderson

## Project Overview

This is a text-based public transport route advisor. It models a small city transport network as stops and travel segments. A user can choose an origin, destination, and travel preference, then generate possible journeys and rank them according to the selected preference.

The default example network is based on Hong Kong's public transport. It contains 12 stops and 40 segments across MTR, bus, minibus, and walking.

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
  planner.py              Journey generation and ranking algorithm
  file_io.py              Load/save transport network files
  data/
    hk_network.txt        Sample Hong Kong transport network
    test_cases.py         Automated tests and case-study demonstrations
README.md                 Project description/instructions (you are here!)
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

The route planner uses a depth-limited search to generate candidate journeys:

- It starts from the origin stop.
- It follows outgoing segments to adjacent stops.
- It avoids repeating stops in the same journey.
- It stops when the destination is reached, the depth limit is reached, or enough candidate journeys are found.

This approach is intentionally simple for COMP1110. It finds reasonable candidate journeys, but it does not guarantee mathematically optimal routes.

## How to Run Tests

From the `COMP1110` directory:

```powershell
$env:PYTHONPATH='.'; python data\test_cases.py
```

The test suite covers:

- stop, segment, journey, and network model behavior
- file loading and saving
- journey generation
- journey ranking
- four case-study scenarios

Current expected result:

```text
52 passed, 0 failed
```

## Case Studies

The test file includes four case-study demonstrations:

1. Budget commuter: Central to Sha Tin using `cheapest`.
2. Rush-hour student: Tsuen Wan to Causeway Bay using `fastest`.
3. Transfer-averse user: Tseung Kwan O to Tsim Sha Tsui using `fewest_transfers`.
4. Preference comparison: Admiralty to Kowloon Tong using all preference modes.

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
- MTR journeys consisting of more than one segment often generate over-estimated costs
- Fares and durations are simplified sample values.
- Route generation uses a simple depth-limited search and may miss better routes in larger networks.
- Walking links only exist where they are explicitly listed as segments.

## Future Improvements

Possible improvements include:

- adding more stops and more realistic transport data
- adding accessibility preferences
- adding walking-distance estimates
- supporting more detailed transfer penalties
- improving route search with more advanced graph algorithms
- adding clearer report/export formatting for case studies
