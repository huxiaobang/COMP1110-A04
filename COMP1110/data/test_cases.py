"""
test_cases.py - Automated tests and case study demonstrations.
Run with:  python data/test_cases.py   (from the COMP1110 directory)

Covers:
  1. Unit tests for input validation and model logic
  2. Journey generation correctness
  3. Ranking correctness
  4. Case study scenarios
"""

import sys
import os
# Ensure the parent directory (COMP1110/) is on the import path so that
# this script can be run directly from any working directory without
# needing to set PYTHONPATH manually.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Stop, Segment, Journey, TransportNetwork
from file_io import load_network, create_default_network, save_network
from planner import find_journeys, rank_journeys, VALID_PREFERENCES
from planner import find_journeys_dfs, find_journeys_dijkstra, LARGE_NETWORK_THRESHOLD
from main import validate_stop
import os
import builtins

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
    check(j.num_transfers == 1,    "num_transfers = 1 (MTR to Bus)")
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
    check(net.has_stop("A"), "has_stop finds existing stop")
    check(not net.has_stop("Z"), "has_stop rejects unknown stop")
    check(len(net.get_outgoing("A")) == 1, "A has 1 outgoing segment")
    check(len(net.get_outgoing("B")) == 0, "B has 0 outgoing segments")
    check(net.is_reachable("A", "B"), "is_reachable finds connected destination")
    check(not net.is_reachable("B", "A"), "is_reachable respects directed segments")

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
    check(len(journeys) > 0, "CEN to ADM: at least 1 journey found")

    # All journeys should start at CEN and end at ADM
    all_valid = all(j.origin_id == "CEN" and j.destination_id == "ADM"
                    for j in journeys)
    check(all_valid, "All journeys have correct origin/destination")

    # Multi-hop journey
    journeys2 = find_journeys(net, "CEN", "SHA")
    check(len(journeys2) > 0, "CEN to SHA: at least 1 journey found")

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


def test_validate_stop_preserves_custom_id_case():
    print_section("Test: Stop input preserves custom ID case")
    net = TransportNetwork()
    net.add_stop(Stop("a", "Lowercase A"))
    net.add_stop(Stop("ab", "Lowercase AB"))

    original_input = builtins.input
    try:
        responses = iter(["a"])
        builtins.input = lambda prompt: next(responses)
        chosen = validate_stop(net, "  Enter stop: ")
        check(chosen == "a", "Exact lowercase stop ID is selected before uppercase fallback")
    finally:
        builtins.input = original_input


# ================================================================
#  4. Case study scenarios (preview / framework)
# ================================================================

def case_study_budget_commuter():
    """Case Study 1: Budget commuter wants cheapest route."""
    print_section("Case Study 1: Budget Commuter (CEN to SHA, cheapest)")
    net = create_default_network()
    journeys = find_journeys(net, "CEN", "SHA")
    check(len(journeys) > 0, "Found candidate journeys")

    ranked = rank_journeys(journeys, "cheapest")
    best = ranked[0]
    print(f"  Best route: cost=${best.total_cost:.1f}, "
          f"time={best.total_duration:.0f}min, "
          f"segments={best.num_segments}")
    for i, seg in enumerate(best.segments, 1):
        print(f"    {i}. [{seg.transport_type}] {seg.from_stop_id}->{seg.to_stop_id} "
              f"({seg.duration:.0f}min, ${seg.cost:.1f})")
    check(best.total_cost <= ranked[-1].total_cost, "Cheapest is ranked first")


def case_study_rush_hour():
    """Case Study 2: Last-minute student wants fastest route."""
    print_section("Case Study 2: Rush Hour Student (TWN to CWB, fastest)")
    net = create_default_network()
    journeys = find_journeys(net, "TWN", "CWB")
    check(len(journeys) > 0, "Found candidate journeys")

    ranked = rank_journeys(journeys, "fastest")
    best = ranked[0]
    print(f"  Best route: time={best.total_duration:.0f}min, "
          f"cost=${best.total_cost:.1f}, segments={best.num_segments}")
    for i, seg in enumerate(best.segments, 1):
        print(f"    {i}. [{seg.transport_type}] {seg.from_stop_id}->{seg.to_stop_id} "
              f"({seg.duration:.0f}min, ${seg.cost:.1f})")
    check(best.total_duration <= ranked[-1].total_duration, "Fastest is ranked first")


def case_study_transfer_averse():
    """Case Study 3: Transfer-averse user wants fewest transfers."""
    print_section("Case Study 3: Transfer-Averse User (TKO to TST, fewest_transfers)")
    net = create_default_network()
    journeys = find_journeys(net, "TKO", "TST")
    check(len(journeys) > 0, "Found candidate journeys")

    ranked = rank_journeys(journeys, "fewest_transfers")
    best = ranked[0]
    print(f"  Best route: transfers={best.num_transfers}, "
          f"time={best.total_duration:.0f}min, cost=${best.total_cost:.1f}")
    for i, seg in enumerate(best.segments, 1):
        print(f"    {i}. [{seg.transport_type}] {seg.from_stop_id}->{seg.to_stop_id} "
              f"({seg.duration:.0f}min, ${seg.cost:.1f})")
    check(best.num_transfers <= ranked[-1].num_transfers, "Fewest transfers ranked first")


def case_study_preference_comparison():
    """Case Study 4: Compare different preferences for the same trip."""
    print_section("Case Study 4: Preference Comparison (ADM to KOT)")
    net = create_default_network()
    journeys = find_journeys(net, "ADM", "KOT")
    check(len(journeys) > 0, "Found candidate journeys")

    best_by_preference = {}
    for pref in VALID_PREFERENCES:
        best = rank_journeys(journeys, pref)[0]
        best_by_preference[pref] = best
        print(f"  Preference: {pref}")
        print(f"    route={'->'.join(best.get_stop_sequence())}")
        print(f"    time={best.total_duration:.0f}min, "
              f"cost=${best.total_cost:.1f}, "
              f"segments={best.num_segments}, "
              f"transfers={best.num_transfers}")

    fastest = best_by_preference["fastest"]
    cheapest = best_by_preference["cheapest"]
    fewest_segments = best_by_preference["fewest_segments"]
    fewest_transfers = best_by_preference["fewest_transfers"]

    unique_routes = {tuple(j.get_stop_sequence()) for j in best_by_preference.values()}
    check(len(unique_routes) >= 3, "Different preferences produce distinct route choices")
    check(fastest.total_duration <= cheapest.total_duration, "Fastest is quicker than cheapest")
    check(cheapest.total_cost <= fastest.total_cost, "Cheapest costs less than fastest")
    check(fewest_segments.num_segments <= fastest.num_segments,
          "Fewest-segments uses no more legs than fastest")
    check(fewest_transfers.num_transfers <= cheapest.num_transfers,
          "Fewest-transfers reduces transfers compared with cheapest")


# ================================================================
#  5. Dijkstra algorithm tests
# ================================================================

def test_dijkstra_basic():
    print_section("Test: Dijkstra basic correctness")
    net = create_default_network()
    # Dijkstra should find optimal fastest route
    dij = find_journeys_dijkstra(net, "CEN", "SHA", preference="fastest", k=3)
    check(len(dij) >= 1, "Dijkstra finds at least 1 journey")
    check(dij[0].total_duration <= 30, "Dijkstra fastest CEN->SHA <= 30 min")

    # Compare with DFS: Dijkstra best should be <= DFS best
    dfs = find_journeys_dfs(net, "CEN", "SHA")
    dfs_ranked = rank_journeys(dfs, "fastest")
    check(dij[0].total_duration <= dfs_ranked[0].total_duration,
          "Dijkstra optimal <= DFS best for fastest")

    # Cheapest preference
    dij_cheap = find_journeys_dijkstra(net, "CEN", "SHA", preference="cheapest", k=3)
    check(dij_cheap[0].total_cost <= dfs_ranked[0].total_cost,
          "Dijkstra cheapest <= DFS best cost")


def test_dijkstra_unreachable():
    print_section("Test: Dijkstra unreachable destination")
    net = TransportNetwork()
    net.add_stop(Stop("A", "StopA"))
    net.add_stop(Stop("B", "StopB"))
    # No segments - B is unreachable from A
    result = find_journeys_dijkstra(net, "A", "B", preference="fastest", k=3)
    check(result == [], "Dijkstra returns empty list for unreachable destination")


def test_auto_switch():
    print_section("Test: Auto algorithm selection by network size")
    net = create_default_network()
    # Small network (12 stops) should use DFS
    check(len(net.stops) <= LARGE_NETWORK_THRESHOLD,
          f"Sample network ({len(net.stops)} stops) <= threshold ({LARGE_NETWORK_THRESHOLD})")
    # find_journeys with default method on small network gives same results as DFS
    auto_result = find_journeys(net, "CEN", "SHA", preference="fastest")
    dfs_result = find_journeys_dfs(net, "CEN", "SHA")
    check(len(auto_result) == len(dfs_result),
          "Auto selects DFS for small network (same result count)")


# ================================================================
#  6. Case Study 5: Real-data network tests
# ================================================================

def case_study_real_network():
    print_section("Case Study 5: Real-data network")
    filepath = os.path.join("data", "hk_network_real.txt")
    if not os.path.exists(filepath):
        print("  [SKIP] hk_network_real.txt not found (run fetch_real_data.py first)")
        return

    net = load_network(filepath)
    check(len(net.stops) >= 30, f"Real network has >= 30 stops ({len(net.stops)})")
    check(len(net.segments) >= 100, f"Real network has >= 100 segments ({len(net.segments)})")

    # 5a: Walking shortcut TST -> ETS
    j = find_journeys(net, "TST", "ETS", preference="fastest")
    ranked = rank_journeys(j, "fastest")
    check(len(ranked) >= 1, "TST->ETS: route found")
    check(ranked[0].total_duration <= 6, "TST->ETS fastest <= 6 min (walking shortcut)")
    check(ranked[0].total_cost == 0.0, "TST->ETS cheapest uses walking ($0)")

    # 5b: CEN -> SHT multi-modal comparison
    results = {}
    for pref in VALID_PREFERENCES:
        j = find_journeys(net, "CEN", "SHT", preference=pref)
        results[pref] = rank_journeys(j, pref)[0]

    check(results["fastest"].total_duration < results["cheapest"].total_duration,
          "CEN->SHT: fastest is quicker than cheapest")
    check(results["cheapest"].total_cost < results["fastest"].total_cost,
          "CEN->SHT: cheapest costs less than fastest")
    check(results["cheapest"].total_cost < 20.0,
          f"CEN->SHT cheapest uses bus/walk (${results['cheapest'].total_cost:.1f} < $20)")

    # Walking segment used in cheapest route
    walk_used = any(s.transport_type == "Walking" for s in results["cheapest"].segments)
    check(walk_used, "CEN->SHT cheapest route uses walking segment")

    # 5c: Dijkstra guarantees optimality on real network
    check(len(net.stops) > LARGE_NETWORK_THRESHOLD,
          f"Real network ({len(net.stops)} stops) triggers Dijkstra auto-switch")


# ================================================================
#  Run all tests
# ================================================================

def main():
    print("\n" + "=" * 55)
    print("  Smart Public Transport Advisor - Test Suite")
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
    test_validate_stop_preserves_custom_id_case()

    # Case studies
    case_study_budget_commuter()
    case_study_rush_hour()
    case_study_transfer_averse()
    case_study_preference_comparison()

    # Dijkstra tests
    test_dijkstra_basic()
    test_dijkstra_unreachable()
    test_auto_switch()

    # Case study 5 (real network)
    case_study_real_network()

    # Summary
    print(f"\n{'=' * 55}")
    print(f"  Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print(f"{'=' * 55}\n")

    if FAIL > 0:
        print("  [FAIL] Some tests failed. Review output above.")
    else:
        print("  [PASS] All tests passed!")


if __name__ == "__main__":
    main()
