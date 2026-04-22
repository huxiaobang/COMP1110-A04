"""
models.py - Core data models for Smart Public Transport Advisor.
Defines Stop, Segment, Journey, and TransportNetwork classes.
"""


class Stop:
    """
    Represents a physical location (station/stop) in the transport network.
    Each stop is uniquely identified by a stop_id.
    """

    def __init__(self, stop_id, name, latitude=0.0, longitude=0.0):
        self.stop_id = stop_id      # Unique identifier, e.g. "CEN"
        self.name = name            # Human-readable name, e.g. "Central"
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return f"Stop({self.stop_id}, '{self.name}')"

    def __eq__(self, other):
        return isinstance(other, Stop) and self.stop_id == other.stop_id

    def __hash__(self):
        return hash(self.stop_id)


class Segment:
    """
    A connection between two stops using a specific transport mode.
    Contains duration (minutes) and cost (HKD).
    """

    def __init__(self, from_stop_id, to_stop_id, transport_type, duration, cost):
        self.from_stop_id = from_stop_id    # Origin stop ID
        self.to_stop_id = to_stop_id        # Destination stop ID
        self.transport_type = transport_type # e.g. "MTR", "Bus", "Minibus", "Walking"
        self.duration = duration             # Travel time in minutes
        self.cost = cost                     # Fare in HKD

    def __repr__(self):
        return (f"Segment({self.from_stop_id}->{self.to_stop_id}, "
                f"{self.transport_type}, {self.duration}min, ${self.cost})")


class Journey:
    """
    A complete route from origin to destination, composed of a sequence of Segments.
    Provides computed properties for total cost, duration, transfers, etc.
    """

    def __init__(self, segments):
        """segments: list of Segment objects forming the journey."""
        self.segments = list(segments)

    # --- Computed properties ---

    @property
    def total_duration(self):
        """Total travel time in minutes."""
        return sum(seg.duration for seg in self.segments)

    @property
    def total_cost(self):
        """Total fare in HKD."""
        return sum(seg.cost for seg in self.segments)

    @property
    def num_segments(self):
        """Number of segments (legs) in the journey."""
        return len(self.segments)

    @property
    def num_transfers(self):
        """
        Number of transfers (changes between different transport types).
        E.g. MTR->MTR = 0 transfers; MTR->Bus = 1 transfer.
        """
        if len(self.segments) <= 1:
            return 0
        transfers = 0
        for i in range(1, len(self.segments)):
            if self.segments[i].transport_type != self.segments[i - 1].transport_type:
                transfers += 1
        return transfers

    @property
    def transport_types_used(self):
        """Set of distinct transport types used in this journey."""
        return sorted(set(seg.transport_type for seg in self.segments))

    @property
    def origin_id(self):
        return self.segments[0].from_stop_id if self.segments else None

    @property
    def destination_id(self):
        return self.segments[-1].to_stop_id if self.segments else None

    def get_stop_sequence(self):
        """Return the ordered list of stop IDs visited."""
        if not self.segments:
            return []
        stops = [self.segments[0].from_stop_id]
        for seg in self.segments:
            stops.append(seg.to_stop_id)
        return stops


class TransportNetwork:
    """
    A graph-based model of a city's transport system.
    Contains stops (nodes) and segments (directed edges).
    """

    def __init__(self):
        self.stops = {}          # stop_id -> Stop
        self.segments = []       # List of all Segment objects
        self._adjacency = {}     # stop_id -> list of outgoing Segments

    def add_stop(self, stop):
        """Add a stop to the network. Raises ValueError if duplicate."""
        if stop.stop_id in self.stops:
            raise ValueError(f"Duplicate stop ID: '{stop.stop_id}'")
        self.stops[stop.stop_id] = stop
        self._adjacency[stop.stop_id] = []

    def add_segment(self, segment):
        """Add a segment. Both endpoints must already exist as stops."""
        if segment.from_stop_id not in self.stops:
            raise ValueError(f"Origin stop '{segment.from_stop_id}' not found.")
        if segment.to_stop_id not in self.stops:
            raise ValueError(f"Destination stop '{segment.to_stop_id}' not found.")
        self.segments.append(segment)
        self._adjacency[segment.from_stop_id].append(segment)

    def get_outgoing(self, stop_id):
        """Return list of segments departing from the given stop."""
        return self._adjacency.get(stop_id, [])

    def get_stop(self, stop_id):
        """Return Stop object or None."""
        return self.stops.get(stop_id)

    def find_stop_by_name(self, name):
        """Case-insensitive exact match by name. Returns Stop or None."""
        for stop in self.stops.values():
            if stop.name.lower() == name.lower():
                return stop
        return None

    def search_stops(self, query):
        """Partial match search. Returns list of matching Stop objects."""
        query_lower = query.lower()
        return [s for s in self.stops.values()
                if query_lower in s.name.lower() or query_lower in s.stop_id.lower()]

    def is_empty(self):
        return len(self.stops) == 0

    def summary_string(self):
        """Return a formatted summary of the network."""
        lines = [
            "=" * 50,
            "  Network Summary",
            "=" * 50,
            f"  Total stops:    {len(self.stops)}",
            f"  Total segments: {len(self.segments)}",
        ]
        # Count by transport type
        type_counts = {}
        for seg in self.segments:
            type_counts[seg.transport_type] = type_counts.get(seg.transport_type, 0) + 1
        lines.append(f"  Transport types:")
        for t in sorted(type_counts):
            lines.append(f"    - {t}: {type_counts[t]} segments")
        lines.append("=" * 50)
        return "\n".join(lines)