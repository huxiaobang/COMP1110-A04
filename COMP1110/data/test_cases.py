"""
test_cases.py - Automated tests and case study demonstrations.
Run with:  python test_cases.py

Covers:
  1. Unit tests for input validation and model logic
  2. Journey generation correctness
  3. Ranking correctness
  4. Case study scenarios
"""

from models import Stop, Segment, Journey, TransportNetwork
from file_io import load_network, create_default_network, save_network
from planner import find_journeys, rank_journeys, VALID_PREFERENCES
import os

PASS = 0
FAIL = 0


def check(condition, description):
    """Simple test assertion with counter."""
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {description}")
    else:
        FAIL += 1
        print(f"  [FAIL] {description}")


def print_section(title):
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print(f"{'=' * 55}")


# ================================================================
#  1. Model unit tests
# ================================================================

def test_stop_creation():
    print_section("Test: Stop creation")
    s = Stop("X1", "Test Stop", 22.0, 114.0)
    check(s.stop_id == "X1",   "stop_id is correct")
    check(s.name == "Test Stop", "name is correct")
    check(s.latitude == 22.0,  "latitude is correct")


def test_segment_creation():
    print_section("Test: Segment creation")
    seg = Segment("A", "B", "MTR", 5.0, 6.5)
    check(seg.from_stop_id == "A",      "from_stop_id correct")
    check(seg.transport_type == "MTR",   "transport_type correct")
    check(seg.duration == 5.0,           "duration correct")
    check(seg.cost == 6.5,              "cost correct")


def test_journey_properties():
    print_section("Test: Journey computed properties")
    segs = [
        Segment("A", "B", "MTR", 5, 6.0),
        Segment("B", "C", "MTR", 3, 4.0),
        Segment("C", "D", "Bus", 8, 5.0),
    ]
    j = Journey(segs)
    check(j.total_duration == 16,   "total_duration = 5+3+8 = 16")
    check(j.total_cost == 15.0,    "total_cost = 6+4+5 = 15")
    check(j.num_segments == 3,     "num_segments = 3")
    check(j.num_transfers == 1,    "num_transfers = 1 (MTR→Bus)")
    check(j.origin_id == "A",      "origin is A")
    check(j.destination_id == "D", "destination is D")
    check(j.get_stop_sequence() == ["A", "B", "C", "D"], "stop sequence correct")


def test_network_operations():
    print_section("Test: TransportNetwork operations")
    net = TransportNetwork()
    net.add_stop(Stop("A", "Alpha"))
    net.add_stop(Stop("B", "Beta"))
    check(len(net.stops) == 2, "2 stops added")

    net.add_segment(Segment("A", "B", "Bus", 10, 5))
    check(len(net.segments) == 1, "1 segment added")
    check(len(net.get_outgoing("A")) == 1, "A has 1 outgoing segment")
    check(len(net.get_outgoing("B")) == 0, "B has 0 outgoing segments")

    # Duplicate stop
    try:
        net.add_stop(Stop("A", "Alpha2"))
        check(False, "Should reject duplicate stop ID")
    except ValueError:
        check(True, "Rejects duplicate stop ID")

    # Segment with unknown stop
    try:
        net.add_segment(Segment("A", "Z", "Bus", 5, 3))
        check(False, "Should reject segment with unknown stop")
    except ValueError:
        check(True, "Rejects segment with unknown destination")

    # Search
    check(net.find_stop_by_name("alpha") is not None, "find_stop_by_name case-insensitive")
    check(len(net.search_stops("a")) >= 1, "search_stops partial match works")


# ================================================================
#  2. File I/O tests
# ================================================================

def test_file_io():
    print_section("Test: File I/O")

    # Save and reload
    net = create_default_network()
    test_path = os.path.join("data", "_test_temp.txt")
    save_network(net, test_path)
    check(os.path.exists(test_path), "File saved successfully")

    loaded = load_network(test_path)
    check(len(loaded.stops) == len(net.stops), "Same number of stops after reload")
    check(len(loaded.segments) == len(net.segments), "Same number of segments after reload")

    # Clean up
    os.remove(test_path)

    # Missing file
    try:
        load_network("nonexistent_file.txt")
        check(False, "Should raise FileNotFoundError")
    except FileNotFoundError:
        check(True, "Raises FileNotFoundError for missing file")

    # Empty file
    empty_path = os.path.join("data", "_test_empty.txt")
    with open(empty_path, "w") as f:
        f.write("# only comments\n")
    try:
        load_network(empty_path)
        check(False, "Should raise ValueError for empty file")
    except ValueError:
        check(True, "Raises ValueError for empty data file")
    os.remove(empty_path)


# ================================================================
#  3. Journey generation & ranking tests
# ================================================================

def test_journey_generation():
    print_section("Test: Journey generation")
    net = create_default_network()

    # Direct neighbours should find at least one journey
    journeys = find_journeys(net, "CEN", "ADM")
    check(len(journeys) > 0, "CEN→ADM: at least 1 journey found")

    # All journeys should start at CEN and end at ADM
    all_valid = all(j.origin_id == "CEN" and j.destination_id == "ADM"
                    for j in journeys)
    check(all_valid, "All journeys have correct origin/destination")

    # Multi-hop journey
    journeys2 = find_journeys(net, "CEN", "SHA")
    check(len(journeys2) > 0, "CEN→SHA: at least 1 journey found")

    # No path (won't happen in default network since it's connected,
    # so we test with a disconnected network)
    iso_net = TransportNetwork()
    iso_net.add_stop(Stop("X", "Isolated X"))
    iso_net.add_stop(Stop("Y", "Isolated Y"))
    journeys3 = find_journeys(iso_net, "X", "Y")
    check(len(journeys3) == 0, "Disconnected stops: 0 journeys")


def test_ranking():
    print_section("Test: Journey ranking")

    # Create journeys with known properties
    j_fast   = Journey([Segment("A", "B", "MTR", 5,  20.0)])  # fast but expensive
    j_cheap  = Journey([Segment("A", "C", "Bus", 30,  3.0),   # cheap but slow
                         Segment("C", "B", "Bus", 20,  2.0)])
    j_direct = Journey([Segment("A", "B", "Walking", 40, 0.0)])  # 1 segment, free

    all_j = [j_fast, j_cheap, j_direct]

    ranked_fast = rank_journeys(all_j, "fastest")
    check(ranked_fast[0] is j_fast, "fastest: MTR journey ranked #1")

    ranked_cheap = rank_journeys(all_j, "cheapest")
    check(ranked_cheap[0] is j_direct, "cheapest: Walking (free) ranked #1")

    ranked_seg = rank_journeys(all_j, "fewest_segments")
    check(ranked_seg[0].num_segments == 1, "fewest_segments: 1-segment journey ranked #1")

    # Invalid preference
    try:
        rank_journeys(all_j, "invalid_pref")
        check(False, "Should raise ValueError for invalid preference")
    except ValueError:
        check(True, "Raises ValueError for invalid preference")


# ================================================================
#  4. Case study scenarios (preview / framework)
# ================================================================

def case_study_budget_commuter():
    """Case Study 1: Budget commuter — wants cheapest route."""
    print_section("Case Study 1: Budget Commuter (CEN → SHA, cheapest)")
    net = create_default_network()
    journeys = find_journeys(net, "CEN", "SHA")
    check(len(journeys) > 0, "Found candidate journeys")

    ranked = rank_journeys(journeys, "cheapest")
    best = ranked[0]
    print(f"  Best route: cost=${best.total_cost:.1f}, "
          f"time={best.total_duration:.0f}min, "
          f"segments={best.num_segments}")
    for i, seg in enumerate(best.segments, 1):
        print(f"    {i}. [{seg.transport_type}] {seg.from_stop_id}→{seg.to_stop_id} "
              f"({seg.duration:.0f}min, ${seg.cost:.1f})")
    check(best.total_cost <= ranked[-1].total_cost, "Cheapest is ranked first")


def case_study_rush_hour():
    """Case Study 2: Last-minute student — wants fastest route."""
    print_section("Case Study 2: Rush Hour Student (TWN → CWB, fastest)")
    net = create_default_network()
    journeys = find_journeys(net, "TWN", "CWB")
    check(len(journeys) > 0, "Found candidate journeys")

    ranked = rank_journeys(journeys, "fastest")
    best = ranked[0]
    print(f"  Best route: time={best.total_duration:.0f}min, "
          f"cost=${best.total_cost:.1f}, segments={best.num_segments}")
    for i, seg in enumerate(best.segments, 1):
        print(f"    {i}. [{seg.transport_type}] {seg.from_stop_id}→{seg.to_stop_id} "
              f"({seg.duration:.0f}min, ${seg.cost:.1f})")
    check(best.total_duration <= ranked[-1].total_duration, "Fastest is ranked first")


def case_study_transfer_averse():
    """Case Study 3: Transfer-averse user — wants fewest transfers."""
    print_section("Case Study 3: Transfer-Averse User (TKO → TST, fewest_transfers)")
    net = create_default_network()
    journeys = find_journeys(net, "TKO", "TST")
    check(len(journeys) > 0, "Found candidate journeys")

    ranked = rank_journeys(journeys, "fewest_transfers")
    best = ranked[0]
    print(f"  Best route: transfers={best.num_transfers}, "
          f"time={best.total_duration:.0f}min, cost=${best.total_cost:.1f}")
    for i, seg in enumerate(best.segments, 1):
        print(f"    {i}. [{seg.transport_type}] {seg.from_stop_id}→{seg.to_stop_id} "
              f"({seg.duration:.0f}min, ${seg.cost:.1f})")
    check(best.num_transfers <= ranked[-1].num_transfers, "Fewest transfers ranked first")


# ================================================================
#  Run all tests
# ================================================================

def main():
    print("\n" + "=" * 55)
    print("  Smart Public Transport Advisor — Test Suite")
    print("=" * 55)

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    # Unit tests
    test_stop_creation()
    test_segment_creation()
    test_journey_properties()
    test_network_operations()
    test_file_io()
    test_journey_generation()
    test_ranking()

    # Case studies
    case_study_budget_commuter()
    case_study_rush_hour()
    case_study_transfer_averse()

    # Summary
    print(f"\n{'=' * 55}")
    print(f"  Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print(f"{'=' * 55}\n")

    if FAIL > 0:
        print("  ⚠  Some tests failed. Review output above.")
    else:
        print("  ✓  All tests passed!")


if __name__ == "__main__":
    main()