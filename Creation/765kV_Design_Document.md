<style>
table { margin-left: auto; margin-right: auto; }
img { display: block; margin-left: auto; margin-right: auto; }
p > strong { text-align: center; display: block; }
</style>

# Synthetic ERCOT Grid — Design Summary

---

## System Overview

**Table 1: System Overview**

| Metric | Value |
|--------|-------|
| Total Substations | 4,519 |
| Core Substations (load/gen) | 4,399 |
| Large-Load Substations | 120 |
| Total Buses | 9,434 |
| Avg Buses per Substation | 2.09 |
| Total System Load | 145,572 MW |
| Total Generation Capacity | ~268,425 MW |
| Weather Zones | 8 |
| Counties | 200 |


---

## Data Sources

**Table 2: Data Sources**

| Data | Source | Description |
|------|--------|-------------|
| Substation locations | U.S. Census Bureau ACS 5-Year (2022) | Census tract centroids used as load fragment locations within ERCOT boundary |
| Operable generation | EIA Form 860 (2022) | Plant coordinates, generator capacity, fuel type, and operational status |
| Planned generation | ERCOT GIS Interconnection Queue (January 2026) | IA-signed approved projects from ERCOT GIS Report (Large Gen + Small Gen sheets) |
| Weather zones | ERCOT Weather Zone Shapefile | 8 ERCOT climate zones used for area assignment |
| County boundaries | U.S. Census Bureau TIGER/Line Shapefiles | Texas county polygons used for zone assignment |
| Reference case | ERCOT 70k-bus PowerWorld Model (ver 30, 2025) | Bus kV distribution and load patterns used as statistical targets |
| Large load spatial pattern | ERCOT 70k-bus Reference Case (PowerWorld) | Loads >= 75 MW extracted and fit to Thomas Cluster Process for synthetic placement |
| Data center locations | IM3 Open Source Data Center Atlas | TX data center coordinates used for DataCenter substation labeling (50 km proximity) |
| 765 kV corridors | ERCOT Permian Basin Transmission Plan | Permian Basin and Eastern corridor waypoints (offset 20-50 km for synthetic grid) |
| System load target | 2031 ERCOT CDR Forecast | 145 GW total system load including ~52 GW large loads |

---

## Weather Zones and Counties

![Weather Zones and Counties](weather_zones_counties.png)

---

## Substation Composition

**Table 3: Substation Composition**

| Type | Count | % of Core |
|------|-------|-----------|
| Load only | 3,568 | 81.1% |
| Gen only | 240 | 5.5% |
| Both load + gen | 591 | 13.4% |
| EHV (>200 kV) | 1,590 | 36.1% |

---

## Voltage Level Distribution

**Table 4: Voltage Level Distribution**

| kV | Buses | % | Reference (ERCOT 70k) |
|----|-------|---|-----------------------|
| 69 | 1,962 | 21.1% | 10,241 (15.3%) |
| 138 | 5,798 | 62.3% | 46,191 (69.2%) |
| 345 | 1,542 | 16.6% | 10,287 (15.4%) |
| 765 | 12 | 0.1% | 0 (0.0%) |
| **Total** | **9,314** | | **66,719** |

> Reference: ERCOT 70k-bus PowerWorld model (ver 30, 2025-11-14)

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

> Reference: Load fragments derived from U.S. Census ACS 2022 tract data, scaled to 2031 ERCOT CDR target (~145 GW)

![Load Distribution](765kV_design_overview_panel1.png)

---

## Load by Voltage Level

**Table 6: Load by Voltage Level**

| kV | Loads | MW |
|----|-------|----|
| 69 | 1,605 | 34,683 |
| 138 | 2,626 | 78,539 |
| 345 | 48 | 32,351 |

---

## Generation (Operable EIA 860)

**Table 7: Operable Generation Summary**

| Metric | Value |
|--------|-------|
| Total Gen Units | 1,551 |
| Total Gen Fragments | 1,136 |
| Total Capacity | 147,977 MW |

> Reference: EIA Form 860 (2022) — operable generators in ERCOT region

---

## Generation (GIS Planned — IA Signed Approved)

**Table 8: Planned Generation by Technology**

| Technology | Units | MW |
|------------|-------|----|
| Solar Photovoltaic | 252 | 60,152 |
| Battery Storage | 209 | 36,598 |
| Onshore Wind | 78 | 17,174 |
| Natural Gas (Steam) | 16 | 5,599 |
| Other | 10 | 925 |
| **Total Planned** | **565** | **120,448** |

> Reference: ERCOT GIS Interconnection Queue Report (January 2026 vintage) — filtered to IA Signed status

---

## Large Load Allocation (2031 CDR Target)

**Table 9: Large Load Allocation**

| Metric | Value |
|--------|-------|
| Total Large Load Target | 52,350 MW |
| Large-Load Substations | 120 (each >= 75 MW) |
| Data Center Substations | 50 (20,782 MW, labeled via IM3 atlas proximity) |


> Data Center labeling: IM3 Open Source Data Center Atlas — large load subs within 50 km of a real TX data center are labeled as DataCenter. All other large loads are generic.

![Large Load Centers](765kV_design_overview_panel3.png)

---

## 765 kV Transmission Corridors

Based on ERCOT's long-range 765 kV transmission plan. Existing 345 kV substations nearest to each corridor waypoint are upgraded. Waypoints are offset ~20-50 km from ERCOT's published locations to maintain the synthetic nature of the grid.

**Table 10: 765 kV Corridor Summary**

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
