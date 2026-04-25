# Case Study Results

This document records reproducible case-study outputs for the Smart Public Transport Advisor. All cases use the built-in Hong Kong sample network with 12 stops and 40 directed segments.

Run command:

```powershell
cd COMP1110
$env:PYTHONPATH='.'; python data\test_cases.py
```

## Case Study 1: Budget Commuter

Goal: A student wants a low-cost route from Central to Sha Tin.

Input:

```text
Origin: CEN (Central)
Destination: SHA (Sha Tin)
Preference: cheapest
```

Best ranked route:

```text
Cost: $19.3 HKD
Time: 53 min
Segments: 3
Route: CEN -> TST -> MKK -> SHA
Steps:
  1. Bus CEN -> TST (20 min, $6.8)
  2. Minibus TST -> MKK (8 min, $4.0)
  3. Bus MKK -> SHA (25 min, $8.5)
```

Discussion: The system correctly prioritizes fare over speed. The route is cheaper than the all-MTR route, but it requires mixed transport modes and more transfer effort. A real app may also consider waiting times, live delays, and walking distance between transfer points.

## Case Study 2: Rush-Hour Student

Goal: A user is running late and wants the fastest route from Tsuen Wan to Causeway Bay.

Input:

```text
Origin: TWN (Tsuen Wan)
Destination: CWB (Causeway Bay)
Preference: fastest
```

Best ranked route:

```text
Time: 27 min
Cost: $43.3 HKD
Segments: 6
Route: TWN -> MKK -> YMT -> TST -> ADM -> WCH -> CWB
Steps:
  1. MTR TWN -> MKK (15 min, $12.0)
  2. MTR MKK -> YMT (2 min, $5.2)
  3. MTR YMT -> TST (2 min, $5.2)
  4. MTR TST -> ADM (4 min, $10.5)
  5. MTR ADM -> WCH (2 min, $5.2)
  6. MTR WCH -> CWB (2 min, $5.2)
```

Discussion: The fastest result is an all-MTR journey. It is quick but expensive in this simplified network because each segment has an individual sample fare. A real journey planner would likely use official fare tables and may combine multiple MTR legs into one charged trip.

## Case Study 3: Transfer-Averse User

Goal: A user prefers fewer transport-type changes from Tseung Kwan O to Tsim Sha Tsui.

Input:

```text
Origin: TKO (Tseung Kwan O)
Destination: TST (Tsim Sha Tsui)
Preference: fewest_transfers
```

Best ranked route:

```text
Transfers: 0
Time: 26 min
Cost: $37.2 HKD
Segments: 5
Route: TKO -> NOP -> CWB -> WCH -> ADM -> TST
Steps:
  1. MTR TKO -> NOP (15 min, $10.5)
  2. MTR NOP -> CWB (3 min, $5.8)
  3. MTR CWB -> WCH (2 min, $5.2)
  4. MTR WCH -> ADM (2 min, $5.2)
  5. MTR ADM -> TST (4 min, $10.5)
```

Discussion: The system selects a route with no transport-type transfer. This is convenient for a transfer-averse user, but the simplified model counts only changes between transport types, not station-platform transfers or walking inside stations.

## Case Study 4: Preference Comparison

Goal: Compare how different preference modes change the recommendation for the same trip from Admiralty to Kowloon Tong.

Input:

```text
Origin: ADM (Admiralty)
Destination: KOT (Kowloon Tong)
Preference modes: fastest, cheapest, fewest_segments, fewest_transfers
```

Best ranked routes by preference:

| Preference | Route | Time | Cost | Segments | Transfers |
| --- | --- | ---: | ---: | ---: | ---: |
| `fastest` | ADM -> TST -> YMT -> MKK -> KOT | 14 min | $29.4 | 4 | 0 |
| `cheapest` | ADM -> WCH -> CEN -> TST -> MKK -> KOT | 59 min | $22.8 | 5 | 4 |
| `fewest_segments` | ADM -> TST -> MKK -> KOT | 18 min | $23.0 | 3 | 2 |
| `fewest_transfers` | ADM -> TST -> YMT -> MKK -> KOT | 14 min | $29.4 | 4 | 0 |

Discussion: This case shows the value of preference-based ranking. The fastest and fewest-transfer choices are the same all-MTR route, while the cheapest option accepts much longer travel time and more transfer changes to reduce cost. The fewest-segments route uses fewer legs than the fastest route but is not the cheapest. A real transport app would also consider live service status, walking time, exact fare rules, and user comfort.

## Overall Evaluation

Strengths:

- The model clearly separates stops, segments, journeys, and ranking preferences.
- Case studies demonstrate different user priorities instead of only one "best" route.
- Outputs are reproducible because the network is static.
- The text interface and simple file format match the COMP1110 project scope.

Limitations:

- The search is depth-limited and does not guarantee globally optimal results.
- Travel times and costs are simplified sample values.
- MTR fare handling is unrealistic because each segment has a separate sample fare.
- The model does not include service frequency, delays, crowding, accessibility, or detailed walking time.
- Transfer counting only checks transport-type changes, not real station transfers.

Future improvements:

- Use more realistic fares and travel times.
- Add transfer penalties and walking-time estimates.
- Expand the network with more stops and routes.
- Add accessibility or low-walking preferences.
- Use a more advanced graph algorithm for larger networks.
