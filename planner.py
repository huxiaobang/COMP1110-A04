"""
planner.py - Journey generation and ranking.

Journey generation uses depth-limited DFS to find all simple paths
(no repeated stops) between origin and destination, up to a maximum depth.

Ranking sorts candidate journeys by the selected preference mode.

Note: This is a basic implementation. Member 3 may enhance the algorithm
      (e.g. add heuristics, pruning, or alternative search strategies).
"""

import heapq

from models import Journey, Segment

# Supported preference modes
VALID_PREFERENCES = ["fastest", "cheapest", "fewest_segments", "fewest_transfers"]

# Threshold: networks larger than this use Dijkstra by default
LARGE_NETWORK_THRESHOLD = 30


def find_journeys_dfs(network, origin_id, destination_id,
                     max_depth=8, max_results=50):
    """
    Generate candidate journeys using depth-limited DFS.

    This is the original simple approach: it enumerates all simple paths
    (no repeated stops) up to a maximum depth.  Works well for small
    networks (< 30 stops) but may be slow for larger ones.

    Args:
        network:        TransportNetwork object
        origin_id:      Starting stop ID
        destination_id: Ending stop ID
        max_depth:      Maximum number of segments in a journey
        max_results:    Stop searching after finding this many journeys

    Returns:
        List of Journey objects (unranked).
    """
    journeys = []

    def _dfs(current_id, visited, path_segments):
        # Stop if we have enough results
        if len(journeys) >= max_results:
            return

        # Found destination: record the journey
        if current_id == destination_id and path_segments:
            journeys.append(Journey(list(path_segments)))
            return

        # Depth limit reached
        if len(path_segments) >= max_depth:
            return

        # Explore neighbours
        for seg in network.get_outgoing(current_id):
            next_id = seg.to_stop_id
            if next_id not in visited:
                visited.add(next_id)
                path_segments.append(seg)
                _dfs(next_id, visited, path_segments)
                path_segments.pop()
                visited.remove(next_id)

    visited = {origin_id}
    _dfs(origin_id, visited, [])
    return journeys


def find_journeys(network, origin_id, destination_id,
                  max_depth=8, max_results=50, method=None,
                  preference="fastest"):
    """
    Unified entry point for journey generation.

    Automatically selects the algorithm:
      - Small networks (<= LARGE_NETWORK_THRESHOLD stops): DFS (enumerates
        many candidate paths for flexible ranking).
      - Large networks (> LARGE_NETWORK_THRESHOLD stops): Dijkstra-based
        k-shortest-paths (efficient, guarantees optimal results).

    The method can be forced via the 'method' argument:
      - "dfs"      : always use DFS
      - "dijkstra" : always use Dijkstra k-shortest-paths

    Args:
        network:        TransportNetwork object
        origin_id:      Starting stop ID
        destination_id: Ending stop ID
        max_depth:      Maximum DFS depth (only used for DFS)
        max_results:    Max journeys to return
        method:         Force algorithm: "dfs", "dijkstra", or None (auto)
        preference:     Preference mode (used by Dijkstra for edge weights)

    Returns:
        List of Journey objects (unranked for DFS, ranked for Dijkstra).
    """
    # Determine which algorithm to use
    if method is None:
        use_dijkstra = len(network.stops) > LARGE_NETWORK_THRESHOLD
    else:
        use_dijkstra = (method == "dijkstra")

    if use_dijkstra:
        return find_journeys_dijkstra(
            network, origin_id, destination_id,
            preference=preference, k=max_results
        )
    else:
        return find_journeys_dfs(
            network, origin_id, destination_id,
            max_depth=max_depth, max_results=max_results
        )


def rank_journeys(journeys, preference):
    """
    Sort journeys by the given preference mode.

    Args:
        journeys:   List of Journey objects.
        preference: One of VALID_PREFERENCES.

    Returns:
        New sorted list of Journey objects (best first).

    Raises:
        ValueError if preference is not recognized.
    """
    key_map = {
        "fastest":          lambda j: (j.total_duration, j.total_cost),
        "cheapest":         lambda j: (j.total_cost, j.total_duration),
        "fewest_segments":  lambda j: (j.num_segments, j.total_duration),
        "fewest_transfers": lambda j: (j.num_transfers, j.total_duration),
    }

    if preference not in key_map:
        raise ValueError(
            f"Unknown preference '{preference}'. "
            f"Valid options: {', '.join(VALID_PREFERENCES)}"
        )

    return sorted(journeys, key=key_map[preference])


# ================================================================
#  Dijkstra-based journey finder
# ================================================================

def _weight_for_preference(segment, preference):
    """Return the numeric edge weight for a given preference mode."""
    if preference == "fastest":
        return segment.duration
    elif preference == "cheapest":
        return segment.cost
    elif preference == "fewest_segments":
        return 1
    elif preference == "fewest_transfers":
        # Transfers are counted between consecutive segments of different
        # transport types, so a single-edge weight cannot capture this
        # perfectly.  We use 1 per segment as a rough proxy; the DFS
        # approach is better suited for this preference.
        return 1
    return segment.duration  # fallback


def find_journeys_dijkstra(network, origin_id, destination_id,
                           preference="fastest", k=5):
    """
    Find up to *k* shortest journeys using a modified Dijkstra / Yen's
    k-shortest-paths approach.

    1. Run Dijkstra once to get the single optimal path.
    2. Use Yen's algorithm to derive up to k-1 alternative paths by
       systematically deviating from previously found paths.

    This guarantees that the first result is optimal for the chosen
    preference (fastest / cheapest / fewest_segments).

    Args:
        network:        TransportNetwork object
        origin_id:      Starting stop ID
        destination_id: Ending stop ID
        preference:     One of VALID_PREFERENCES (used as edge weight)
        k:              Maximum number of journeys to return

    Returns:
        List of Journey objects, sorted by weight (best first).
    """
    # --- helper: single-source Dijkstra returning ONE shortest path ---
    def _dijkstra(src, dst, blocked_edges=None, blocked_nodes=None):
        """
        Standard Dijkstra.  Returns (cost, [Segment, ...]) or None.
        blocked_edges: set of (from_id, to_id, transport_type) to skip
        blocked_nodes: set of stop_ids to skip (except src and dst)
        """
        if blocked_edges is None:
            blocked_edges = set()
        if blocked_nodes is None:
            blocked_nodes = set()

        # (cumulative_weight, tie_breaker, current_stop, [segments])
        counter = 0
        heap = [(0, counter, src, [])]
        best = {}  # stop_id -> best weight seen so far

        while heap:
            w, _, cur, path = heapq.heappop(heap)

            if cur == dst and path:
                return (w, path)

            if cur in best:
                continue
            best[cur] = w

            for seg in network.get_outgoing(cur):
                nxt = seg.to_stop_id
                edge_key = (seg.from_stop_id, seg.to_stop_id, seg.transport_type)
                if nxt in best:
                    continue
                if nxt in blocked_nodes and nxt != dst:
                    continue
                if edge_key in blocked_edges:
                    continue

                nw = w + _weight_for_preference(seg, preference)
                counter += 1
                heapq.heappush(heap, (nw, counter, nxt, path + [seg]))

        return None  # destination unreachable

    # --- Yen's k-shortest paths ---
    result_paths = []  # list of (weight, [Segment, ...])
    candidates = []    # min-heap of (weight, tie, [Segment, ...])
    tie = 0

    first = _dijkstra(origin_id, destination_id)
    if first is None:
        return []

    result_paths.append(first)

    for i in range(1, k):
        prev_weight, prev_segs = result_paths[i - 1]
        prev_stops = [origin_id] + [s.to_stop_id for s in prev_segs]

        for j in range(len(prev_segs)):
            spur_node = prev_stops[j]
            root_path = prev_segs[:j]
            root_weight = sum(_weight_for_preference(s, preference) for s in root_path)

            # Block edges used by existing results at this spur point
            blocked_edges = set()
            for _, rsegs in result_paths:
                rstops = [origin_id] + [s.to_stop_id for s in rsegs]
                if rstops[:j + 1] == prev_stops[:j + 1] and j < len(rsegs):
                    seg = rsegs[j]
                    blocked_edges.add((seg.from_stop_id, seg.to_stop_id,
                                       seg.transport_type))

            # Block nodes in root path (except spur node)
            blocked_nodes = set(prev_stops[:j])

            spur = _dijkstra(spur_node, destination_id,
                             blocked_edges, blocked_nodes)
            if spur is not None:
                total_weight = root_weight + spur[0]
                total_path = root_path + spur[1]
                # Avoid duplicates
                total_stops = tuple([origin_id] + [s.to_stop_id for s in total_path])
                is_dup = False
                for _, existing in result_paths:
                    es = tuple([origin_id] + [s.to_stop_id for s in existing])
                    if es == total_stops:
                        is_dup = True
                        break
                if not is_dup:
                    tie += 1
                    heapq.heappush(candidates, (total_weight, tie, total_path))

        if not candidates:
            break

        # Pop the best candidate
        best_w, _, best_path = heapq.heappop(candidates)
        result_paths.append((best_w, best_path))

    return [Journey(segs) for _, segs in result_paths]
