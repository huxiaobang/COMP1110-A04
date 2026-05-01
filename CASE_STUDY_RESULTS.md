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

### Case Studies 1–4 (Sample Network)

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

### Case Study 5 (Real-Data Network)

Strengths:

- Real Octopus fares from the MTR open-data API make cost comparisons meaningful.
- Walking segments demonstrate a unique feature not found in single-operator apps.
- Dijkstra algorithm guarantees optimal results for each preference mode.
- Multi-modal routing produces diverse, realistic journey options.

Limitations:

- MTR fares are per adjacent-station segment, not true end-to-end fares.
- Bus/minibus data is hand-curated, not from a live API.
- 36 stations is still a simplified subset of the full HK transport network.

### Future Improvements

- Expand the real-data network to cover more stations and bus/minibus routes.
- Add real-time ETA data from MTR and KMB APIs.
- Support student, child, and elderly concession fares.
- Add accessibility preferences (e.g., barrier-free routes).
- Estimate walking segments automatically from station coordinates.
- Implement true end-to-end MTR fare calculation instead of per-segment accumulation.

---

## Case Study 5: Real-Data Network — Walking Shortcuts and Multi-Modal Routing

This case study uses the 36-stop real-data network fetched from Hong Kong government open-data APIs (menu option 9). It demonstrates two key features that the sample network cannot fully showcase: (i) walking segments as genuine shortcuts between nearby stations on different MTR lines, and (ii) the Dijkstra algorithm handling a larger, more complex network.

### 5a: Walking Shortcut — TST to East TST

Goal: A user wants to travel from Tsim Sha Tsui (Tsuen Wan Line) to East Tsim Sha Tsui (Tuen Ma Line). In reality these two stations are connected by an underground pedestrian passage, but they are on different MTR lines with no in-station interchange.

Input:

```text
Network: hk_network_real.txt (36 stops, 122 segments)
Origin: TST (Tsim Sha Tsui)
Destination: ETS (East Tsim Sha Tsui)
Preference: fastest
```

Results (top 2):

| # | Route | Time | Cost | Type |
|---|-------|-----:|-----:|------|
| 1 | TST → ETS (walk) | 5 min | $0.0 | Walking |
| 2 | TST → JOR → YMT → HOM → HUH → ETS | 13 min | $24.3 | MTR |

Discussion: The system correctly identifies the 5-minute underground walking passage as both the fastest and cheapest option. Without this hand-curated walking segment, the only alternative would be a 13-minute, $24.3 MTR detour through 5 stations. This demonstrates why walking links between nearby stations on different lines are a valuable feature — they reflect how real commuters actually travel. Existing tools like Google Maps and Citymapper also recommend this walking connection, but single-operator apps (e.g., MTR Mobile) would only show the MTR-only route.

### 5b: Multi-Modal Budget Route — Central to Sha Tin

Goal: Compare how the same origin-destination pair produces different recommendations under each preference mode, using real fare data from the MTR API.

Input:

```text
Network: hk_network_real.txt (36 stops, 122 segments)
Origin: CEN (Central)
Destination: SHT (Sha Tin)
Preference: all four modes
```

Results:

| Preference | Route | Time | Cost | Segs | Xfer | Types |
|------------|-------|-----:|-----:|-----:|-----:|-------|
| `fastest` | CEN → ADM → HUH → MKK → KOT → TAW → SHT | 27 min | $36.2 | 6 | 0 | MTR |
| `cheapest` | CEN → WAC → ADM → SHT | 65 min | $15.9 | 3 | 2 | Minibus, Walking, Bus |
| `fewest_segments` | CEN → ADM → SHT | 42 min | $17.3 | 2 | 1 | MTR, Bus |
| `fewest_transfers` | CEN → ADM → TST → JOR → YMT → HOM → DIH → TAW → SHT | 33 min | $53.0 | 8 | 0 | MTR |

Discussion:

- **fastest** uses a direct MTR path via East Rail Line (ADM → HUH → MKK → KOT → TAW → SHT), taking only 27 minutes. The $36.2 fare reflects real adjacent-station Octopus fares from the API.
- **cheapest** creatively combines a minibus (CEN→WAC, $3.5), walking (WAC→ADM, $0), and a cross-harbour bus (ADM→SHT, $12.4) to achieve $15.9 — less than half the MTR fare — but at the cost of 65 minutes.
- **fewest_segments** finds a 2-leg journey: MTR to Admiralty then a direct bus to Sha Tin. This minimizes the number of boarding actions.
- **fewest_transfers** stays entirely on MTR (0 transport-type changes) but takes a longer route through Kowloon, costing $53.0 — the most expensive option.

The walking segment (WAC→ADM, 15 min, $0) plays a critical role in the cheapest route: it connects the minibus drop-off at Wan Chai to Admiralty for free, enabling the cheap bus transfer. Without this walking link, the cheapest route would need to use MTR between WAC and ADM (adding $4.9).

### 5c: Sample vs Real Network Comparison — Central to Sha Tin

To illustrate the improvement from real data, we compare the same query on both networks:

| | Sample Network (12 stops) | Real Network (36 stops) |
|---|---|---|
| **Fastest route** | CEN→ADM→TST→YMT→MKK→KOT→SHA (26 min, $37.9) | CEN→ADM→HUH→MKK→KOT→TAW→SHT (27 min, $36.2) |
| **Cheapest route** | CEN→TST→MKK→SHA (53 min, $19.3) | CEN→WAC→ADM→SHT (65 min, $15.9) |
| **Fare source** | Hand-crafted estimates | Real Octopus fares from MTR API |
| **Algorithm** | DFS (12 stops) | Dijkstra (36 stops) |
| **Walking used?** | No | Yes (cheapest route uses WAC→ADM walk) |

Key differences:

- The real network finds a cheaper route ($15.9 vs $19.3) by leveraging walking and bus segments that were not available in the sample network.
- The real network's fares come from the official MTR open-data API, making the cost comparison more meaningful.
- The larger network triggers Dijkstra, which guarantees optimality for the selected preference — unlike DFS which may miss better routes.

### Evaluation of Case Study 5

What worked well:

- Walking segments correctly serve as both cost-savers (free transfers) and time-savers (shortcuts between lines).
- The Dijkstra algorithm efficiently handles the 36-stop network and guarantees optimal results.
- Real API fares make the cost comparisons meaningful rather than arbitrary.
- Multi-modal routing (MTR + Bus + Minibus + Walking) produces realistic and diverse journey options.

What did not work well:

- MTR fares are still per-segment (adjacent station OD pairs) rather than true end-to-end fares; a real 6-stop MTR journey would cost less than the sum of 6 individual segment fares.
- Bus durations are estimates, not live data.
- The network only covers 36 stations; routes involving unlisted stations (e.g., Fo Tan, Diamond Hill on East Rail) would require more stops.

How existing tools handle this:

- Google Maps and Citymapper would show the walking shortcut (TST→ETS) and provide real-time ETAs.
- MTR Mobile would only suggest MTR-only routes and would not show the walking option.
- Our system sits in between: it uses real fare data and curated walking links, but lacks real-time information.
