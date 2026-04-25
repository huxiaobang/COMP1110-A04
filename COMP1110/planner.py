"""
planner.py - Journey generation and ranking.

Journey generation uses depth-limited DFS to find all simple paths
(no repeated stops) between origin and destination, up to a maximum depth.

Ranking sorts candidate journeys by the selected preference mode.

Note: This is a basic implementation. Member 3 may enhance the algorithm
      (e.g. add heuristics, pruning, or alternative search strategies).
"""

from models import Journey

# Supported preference modes
VALID_PREFERENCES = ["fastest", "cheapest", "fewest_segments", "fewest_transfers"]


def find_journeys(network, origin_id, destination_id,
                  max_depth=8, max_results=50):
    """
    Generate candidate journeys using depth-limited DFS.

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
