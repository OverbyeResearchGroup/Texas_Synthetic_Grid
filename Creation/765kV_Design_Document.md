<style>
table { margin-left: auto; margin-right: auto; }
img { display: block; margin-left: auto; margin-right: auto; }
p > strong { text-align: center; display: block; }
</style>

# Synthetic ERCOT Grid — Substation Design Summary

---

## System Overview

**Table 1: System Overview**

| Metric | Value |
|--------|-------|
| Total Substations | 5,443 |
| Core Substations (load/gen) | 5,197 |
| Large-Load Substations (>75 MW) | 246 (tunable) |
| Total Buses | 9,304 |
| Avg Buses per Substation | 1.71 |
| Total System Load | 145,601 MW |
| Total Generation Capacity | 260,420 MW |
| Weather Zones | 8 |
| Areas | 8 |
| Counties | 200 |

---

## Data Sources

**Table 2: Data Sources**

| Data | Source | Description |
|------|--------|-------------|
| Substation locations | U.S. Census Bureau ACS 5-Year (2022) | Census tract centroids used as load fragment locations within ERCOT boundary |
| Operable generation | EIA Form 860 (2024) | Plant coordinates, generator capacity, fuel type, and operational status |
| Planned generation | ERCOT GIS Interconnection Queue (Jan 2026) | IA-signed approved projects from ERCOT GIS Report |
| Weather zones | ERCOT Weather Zone Shapefile | 8 ERCOT climate zones used for area assignment |
| County boundaries | U.S. Census Bureau TIGER/Line Shapefiles | Texas county polygons used for zone assignment |
| Reference case | 2026 ERCOT 70k-bus PowerWorld model (ver 30) | Bus kV distribution and load patterns used as statistical targets (validation only) |
| Large load spatial pattern | ERCOT 70k-bus Reference Case | Loads >= 75 MW extracted and used to fit synthetic large load placement |
| Data center locations | IM3 Open Source Data Center Atlas | TX data center coordinates for DataCenter labeling (50 km proximity) |
| 765 kV corridors | ERCOT Permian Basin Transmission Plan | Corridor waypoints (offset 20-50 km for synthetic grid) |
| System load target | 2031 ERCOT CDR Forecast | 145 GW total system load including ~52 GW large loads |

---

## Weather Zones and Counties

![ERCOT Weather Zones and Texas Counties](weather_zones_counties.png)

---

## Substation Composition

**Table 3: Substation Composition**

| Type | Count | % of Core |
|------|-------|-----------|
| Load only | 3,568 | 81.1% |
| Gen only | 240 | 5.5% |
| Both load + gen | 591 | 13.4% |
| EHV (>200 kV) | 1,564 | 30.1% |

---

## Voltage Level Distribution

**Table 4: Voltage Level Distribution by Buses**

| kV | Synthetic | Reference Case |
|----|-----------|----------------|
| 69 | 1,969 (21.1%) | 10,241 (15.3%) |
| 138 | 5,798 (62.2%) | 46,191 (69.2%) |
| 345 | 1,542 (16.5%) | 10,287 (15.4%) |
| 765 | 12 (0.1%) | 0 (0.0%) |
| **Total** | **9,321** | **66,719** |

> Reference case: 2026 ERCOT 70k-bus PowerWorld model (ver 30, 2025-11-14)

![Voltage Level Distribution](765kV_design_overview_panel4.png)

---

## Load Distribution by Weather Zone

**Table 5: Load Distribution by Weather Zone**

| Zone | Share | MW |
|------|-------|----|
| North Central | 26.6% | 38,722 |
| Coast | 23.5% | 34,210 |
| South Central | 14.1% | 20,525 |
| Far West | 12.4% | 18,051 |
| West | 9.4% | 13,684 |
| South | 7.4% | 10,772 |
| North | 3.7% | 5,386 |
| East | 3.1% | 4,513 |

> Load fragments derived from U.S. Census ACS 2022 tract data, scaled to 2031 ERCOT CDR target (~145 GW)

![Load Distribution](765kV_design_overview_panel1.png)

---

## Generation (Operable — EIA Form 860)

**Table 6: Operable Generation Summary**

| Metric | Value |
|--------|-------|
| Total Gen Units | 1,551 |
| Total Plants | 1,136 |
| Total Capacity | 147,977 MW |

> Source: EIA Form 860 (2024) — operable generators in ERCOT region

---

## Generation (Planned — GIS IA Signed)

**Table 7: Planned Generation by Technology**

| Technology | Units | MW |
|------------|-------|----|
| Solar Photovoltaic | 252 | 60,152 |
| Battery Storage | 209 | 36,598 |
| Onshore Wind | 78 | 17,174 |
| Natural Gas (Gas) | 16 | 5,599 |
| Other | 10 | 925 |
| **Total Planned** | **565** | **120,448** |

> Source: ERCOT GIS Interconnection Queue Report (January 2026) — filtered to IA Signed status

---

## Combined Generation by Fuel Type

**Table 8: Combined Generation (EIA Operable + GIS Planned)**

| Fuel | Units | Synthetic (MW) | Reference (MW) | Diff (%) |
|------|-------|---------------|---------------|----------|
| Biomass | 1 | 100 | 131 | -23.7% |
| Coal | 26 | 14,598 | 11,596 | +25.9% |
| Diesel | 296 | 629 | 333 | +88.9% |
| Gas, Combined Cycle | 266 | 39,649 | 33,341 | +18.9% |
| Gas Turbine | 396 | 11,692 | 9,723 | +20.3% |
| Gas, Steam Turbine | 72 | 17,586 | 10,383 | +69.4% |
| Hydro | 25 | 472 | 569 | -17.0% |
| Nuclear | 5 | 4,994 | 4,973 | +0.4% |
| Solar | 380 | 77,899 | 94,375 | -17.5% |
| Battery Storage | 318 | 42,116 | 61,258 | -31.2% |
| Wind | 257 | 50,328 | 50,006 | +0.6% |
| Other | 17 | 357 | 0 | N/A |
| **Total** | **2,059** | **260,420** | **276,688** | **-5.9%** |

> Synthetic: EIA operable (2024) + GIS planned (IA Signed, Jan 2026). Reference: 2031 ERCOT case target.

---

## Load by Voltage Level

**Table 9: Load by Voltage Level**

| kV | Loads | MW |
|----|-------|----|
| 69 | 1,658 | 43,370 |
| 138 | 4,695 | 89,843 |
| 345 | 22 | 12,388 |

> Loads are allocated to bus voltage levels based on reference case statistics. Loads below 50 MW at 345 kV substations are placed on the 138 kV bus instead. Only the highest-MW substations get loads split across multiple voltage levels. See notebook Cell 16 for detailed assignment rules.

---

## Large Load Allocation (2031 CDR Target)

**Table 10: Large Load Allocation**

| Metric | Value |
|--------|-------|
| Total Large Load MW | 47,710 MW |
| Large-Load Substations | 246 (tunable, each >= 75 MW) |
| Avg Load Size | ~194 MW |


> The number of large loads is tunable. Each load size is sampled from the ERCOT 2026 reference case distribution. To reach a higher total MW target, either increase the number of loads or scale the individual load sizes.

![2031 ERCOT CDR Large Load Forecast](tsp-large-load-breakdown.png)

### Large Load Design Assumptions

Based on publicly available ERCOT interconnection queue data (~238,000 MW of requests):

**Table 11: Large Load Types (ERCOT Queue Proportions)**

| # | Type | % of MW | Dispatch Assumptions |
|---|------|---------|---------------------|
| 1 | Data Centers | 77.6% (~184,916 MW) | Firm, non-interruptible baseload; no price responsiveness; model as constant-power loads |
| 2 | None / No type provided | 11.1% | Expected to consist largely of data centers; apply data center dispatch assumptions |
| 3 | Crypto Mining | 6.8% | Highly price-elastic; model as Controllable Load Resources with bid curves; can shed hundreds of MW within minutes |
| 4 | Industrial | 2.7% | Mostly firm; approximately 10-20% curtailable at high prices |
| 5 | Data Center / Crypto mixed | 1.1% | Apply crypto dispatch assumptions given price-responsive characteristics |
| 6 | Hydrogen Electrolysis | 0.6% | Flexible load with ramp constraints; can modulate output over minutes to hours |
| 7 | Unknown | 0.1% | Expected to be data centers and crypto; apply proportional dispatch assumptions |

For loads under 75 MW, the standard census/population distribution method is used.

### Current Large Load Assignment

**Table 12: Synthetic Case Large Load Distribution**

| Type | Subs | MW | % of Total |
|------|------|----|-----------|
| DataCenter | 88 | 11,450 | 24.0% |
| LargeLoad (unassigned) | 158 | 36,261 | 76.0% |
| **Total** | **246** | **47,710** | **100%** |

> DataCenter labeling is based on proximity to real TX data center coordinates from the IM3 Open Source Data Center Atlas (within 50 km). All 92 IM3 TX data centers are located east of -98.8° longitude — no data centers exist in the West or Far West weather zones.

![Large Load Centers by Type](765kV_design_overview_panel3.png)

> **Note:** Using the IM3 Open Source Data Center Atlas (50 km proximity), only ~24% of large load MW is currently labeled as DataCenter. According to ERCOT interconnection queue data, data centers account for ~77% of large load demand. Closing this gap would require additional geographic data sources for data center locations beyond what IM3 currently provides.

---

## 765 kV Transmission Corridors

Based on ERCOT's long-range 765 kV transmission plan. Existing 345 kV substations nearest to each corridor waypoint are upgraded. Waypoints are offset ~20-50 km from ERCOT's published locations to maintain the synthetic nature of the grid.

**Table 13: 765 kV Corridor Summary**

| Route | Segment | Substations |
|-------|---------|-------------|
| Permian Basin | West (NM border) | 3 |
| Permian Basin | Middle (central TX) | 5 |
| Eastern | DFW to Gulf Coast | 4 |
| **Total** | | **12** |

> Reference: ERCOT Permian Basin Transmission Plan (765 kV corridors)

![ERCOT 765 kV Reference](Permian_basin_765KV_route.png)

![765 kV Substation Locations](765kV_design_overview_panel2.png)

**Permian Basin Route:** Far west Texas (NM border) through the Permian Basin to central Texas and the DFW area. Serves renewable generation export and west Texas load growth.

**Eastern Route:** DFW hub east toward Arkansas/Louisiana border and south along the Gulf Coast. Serves data centers, industrial loads, and coastal population centers.

---

## Open Questions

1. Should we use the ERCOT Weather Zone or Load Zone to define the ERCOT boundary? Currently, the algorithm is configured to use the Weather Zone.

2. For the 765 kV substation placement, we estimated locations by referencing the Permian Basin 765 kV layout from the provided figure and introducing noise to avoid CEII concerns. Is this an acceptable methodology?
