"""
large_load_allocation.py
========================
Synthetic large-load spatial allocation for the ERCOT synthetic grid.

Algorithm
---------
1. Extract large loads (>= LARGE_LOAD_MW) from PowerWorld reference case
2. Spatial-join to ERCOT weather zones -> build area statistics
3. Fit Thomas Cluster Process (Ripley K/L functions) to observed spatial pattern
4. Generate synthetic load locations via area-aware Gaussian scatter
5. Assign MW values from per-zone lognormal distributions

ERCOT Design Criterion: large load threshold = 75 MW

Author: Texas A&M Synthetic Grid Project
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from scipy.stats import lognorm
from scipy.optimize import minimize

# ── Constants ──────────────────────────────────────────────────────────────────
LARGE_LOAD_MW = 75  # ERCOT design criterion: loads >= 75 MW are "large loads"


# ── Step 1: Extract Reference Large Loads from PowerWorld ──────────────────────

def extract_reference_large_loads(saw, threshold_mw=LARGE_LOAD_MW):
    """
    Extract large loads from a PowerWorld reference case via ESA/SAW.

    Queries Load (BusNum, LoadMW) and Bus (BusNum, Latitude, Longitude),
    joins them, and filters to loads >= threshold_mw within valid coordinates.

    Parameters
    ----------
    saw : SAW
        Open SAW connection to the reference case.
    threshold_mw : float
        MW threshold for "large" loads (default: 75, ERCOT criterion).

    Returns
    -------
    pd.DataFrame with columns: BusNum, LoadID, LoadMW, Latitude, Longitude
    """
    ## TODO: Should I use LoadMW (Online) or LoadSMW(Pure MW without status)? For now, using LoadMW which reflects actual load in the case.
    load_df = saw.GetParametersMultipleElement('Load', ['BusNum', 'LoadID', 'LoadMW'])
    load_df['LoadMW'] = pd.to_numeric(load_df['LoadMW'], errors='coerce').fillna(0)
    large = load_df[load_df['LoadMW'] >= threshold_mw].copy()
    print(f"  Step 1 — loads >= {threshold_mw} MW: {len(large)}")

    # Bus lat/lon is stored on Substation, not Bus — need 3-step join:
    # Load (BusNum) → Bus (BusNum → SubNum) → Substation (SubNum → Lat/Lon)
    bus_df = saw.GetParametersMultipleElement('Bus', ['BusNum', 'SubNum'])
    print(f"  Step 2 — bus rows: {len(bus_df)}, SubNum sample: {bus_df['SubNum'].head(3).tolist()}")

    sub_df = saw.GetParametersMultipleElement('Substation', ['SubNum', 'Latitude', 'Longitude'])
    sub_df['Latitude']  = pd.to_numeric(sub_df['Latitude'],  errors='coerce')
    sub_df['Longitude'] = pd.to_numeric(sub_df['Longitude'], errors='coerce')
    valid_subs = sub_df[(sub_df['Latitude'].abs() > 0.1) & (sub_df['Longitude'].abs() > 0.1)]
    print(f"  Step 3 — substations with valid lat/lon: {len(valid_subs)} of {len(sub_df)}")
    print(f"           Lat range: {sub_df['Latitude'].min():.2f} to {sub_df['Latitude'].max():.2f}")
    print(f"           Lon range: {sub_df['Longitude'].min():.2f} to {sub_df['Longitude'].max():.2f}")

    merged = large.merge(bus_df[['BusNum', 'SubNum']], on='BusNum', how='left')
    print(f"  Step 4 — after Load→Bus join: {len(merged)}, SubNum NaN: {merged['SubNum'].isna().sum()}")

    merged = merged.merge(sub_df[['SubNum', 'Latitude', 'Longitude']], on='SubNum', how='left')
    print(f"  Step 5 — after Bus→Sub join: {len(merged)}, Lat NaN: {merged['Latitude'].isna().sum()}")

    merged = merged.dropna(subset=['Latitude', 'Longitude'])
    merged = merged[(merged['Latitude'].abs() > 0.1) & (merged['Longitude'].abs() > 0.1)]

    print(f"Reference case: {len(merged)} large loads (>= {threshold_mw} MW)")
    return merged.reset_index(drop=True)


# ── Step 2: Build Area Statistics ─────────────────────────────────────────────

def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    return R * 2 * np.arcsin(np.sqrt(a))


def _fill_missing_zone(gdf, zone_gdf, zone_col):
    """Fill missing zone assignments by nearest zone centroid."""
    missing = gdf[zone_col].isna()
    if not missing.any():
        return gdf
    centroids = zone_gdf[zone_gdf[zone_col].notna()].copy()
    centroids['cx'] = centroids.geometry.centroid.x
    centroids['cy'] = centroids.geometry.centroid.y
    for idx in gdf[missing].index:
        pt = gdf.loc[idx, 'geometry']
        dists = (centroids['cx'] - pt.x)**2 + (centroids['cy'] - pt.y)**2
        gdf.loc[idx, zone_col] = centroids.loc[dists.idxmin(), zone_col]
    return gdf


def build_area_stats(loads_df, weather_zone_gdf, zone_col='ERCOT_Clim'):
    """
    Build per-weather-zone statistics from reference large loads.

    Spatially joins loads to weather zones, then computes:
      - NumLoads: count per zone
      - CentroidLat/Lon: geographic center of loads in zone
      - MeanSpread_km: mean haversine distance from centroid

    Parameters
    ----------
    loads_df : pd.DataFrame
        Reference large loads with Latitude, Longitude, LoadMW columns.
    weather_zone_gdf : GeoDataFrame
        ERCOT weather zone shapefile (must have zone_col + geometry).
    zone_col : str
        Column name for weather zone identifier.

    Returns
    -------
    area_stats_df : pd.DataFrame
        Columns: AreaName, NumLoads, CentroidLat, CentroidLon, MeanSpread_km, StdSpread_km
    loads_gdf : GeoDataFrame
        Reference loads with zone_col assigned (used for MW fitting).
    """
    gdf = gpd.GeoDataFrame(
        loads_df.copy(),
        geometry=gpd.points_from_xy(loads_df['Longitude'], loads_df['Latitude']),
        crs='EPSG:4326'
    )
    gdf = gpd.sjoin(gdf, weather_zone_gdf[[zone_col, 'geometry']], how='left', predicate='within')
    gdf = gdf.drop(columns=['index_right'], errors='ignore')
    gdf = _fill_missing_zone(gdf, weather_zone_gdf, zone_col)

    rows = []
    for zone, grp in gdf.groupby(zone_col):
        lats = grp['Latitude'].values
        lons = grp['Longitude'].values
        cLat, cLon = lats.mean(), lons.mean()
        if len(grp) > 1:
            spreads = [_haversine_km(cLat, cLon, la, lo) for la, lo in zip(lats, lons)]
            mean_spread = float(np.mean(spreads))
            std_spread  = float(np.std(spreads))
        else:
            mean_spread = std_spread = 0.0
        rows.append({
            'AreaName':      zone,
            'NumLoads':      len(grp),
            'CentroidLat':   cLat,
            'CentroidLon':   cLon,
            'MeanSpread_km': mean_spread,
            'StdSpread_km':  std_spread,
        })

    area_stats_df = pd.DataFrame(rows)
    print(f"Area stats built for {len(area_stats_df)} weather zones "
          f"({len(gdf)} total reference large loads)")
    return area_stats_df, gdf


# ── Step 3: Thomas Cluster Process Fitting ────────────────────────────────────

def _thomas_K(r, kappa, sigma):
    """K-function for the Thomas cluster process."""
    return np.pi * r**2 + (1.0 / kappa) * (1.0 - np.exp(-r**2 / (4.0 * sigma**2)))


def _objective_L(params, r_obs, L_obs):
    """Minimize squared error between observed L-function and Thomas L-function."""
    kappa, sigma = params
    if kappa <= 0 or sigma <= 0:
        return 1e20
    L_thomas = np.sqrt(_thomas_K(r_obs, kappa, sigma) / np.pi) - r_obs
    return np.sum((L_obs - L_thomas)**2)


def fit_thomas_process(loads_df, n_unique_areas):
    """
    Fit Thomas Cluster Process parameters to reference large load locations.

    Uses Ripley's L-function and Nelder-Mead optimization to estimate:
      kappa  - cluster intensity (clusters per m²)
      sigma  - cluster spread (meters)

    Parameters
    ----------
    loads_df : pd.DataFrame
        Reference large loads with Latitude, Longitude columns.
    n_unique_areas : int
        Number of unique weather zones (used as initial kappa estimate).

    Returns
    -------
    kappa_est, sigma_est, n_clusters_est, mu_est : floats
    """
    from scipy.spatial.distance import pdist, squareform
    from pyproj import Transformer

    lats = loads_df['Latitude'].values
    lons = loads_df['Longitude'].values
    n_points = len(lats)

    if n_points < 5:
        raise ValueError(f"Too few large loads ({n_points}) to fit Thomas process — need >= 5.")

    # Project to UTM
    center_lat, center_lon = lats.mean(), lons.mean()
    zone_num = int(np.floor((center_lon + 180) / 6) + 1)
    epsg = 32600 + zone_num if center_lat >= 0 else 32700 + zone_num
    transformer = Transformer.from_crs('EPSG:4326', f'EPSG:{epsg}', always_xy=True)
    x_utm, y_utm = transformer.transform(lons, lats)

    # Study area (bounding box + 10 km buffer)
    buf = 10_000  # meters
    study_area_m2 = (x_utm.max() - x_utm.min() + 2*buf) * (y_utm.max() - y_utm.min() + 2*buf)
    intensity = n_points / study_area_m2

    # Pairwise UTM distances
    coords = np.column_stack([x_utm, y_utm])
    dist_matrix = squareform(pdist(coords))

    # Ripley's K and L functions (r: 0 to 200 km, 100 steps)
    r_values_m = np.linspace(0, 200_000, 100)
    K_observed = np.array([
        np.sum((dist_matrix < r) & (dist_matrix > 0)) / (n_points * intensity)
        for r in r_values_m
    ])
    L_observed = np.sqrt(K_observed / np.pi) - r_values_m

    # Initial parameter estimates
    peak_idx = max(1, int(np.argmax(L_observed[1:])) + 1)
    sigma0   = r_values_m[peak_idx] / 2.0
    kappa0   = max(n_unique_areas / study_area_m2, intensity / 10)

    r_fit = r_values_m[1:]
    L_fit = L_observed[1:]

    result = minimize(
        _objective_L, x0=[kappa0, sigma0], args=(r_fit, L_fit),
        method='Nelder-Mead',
        options={'maxiter': 100_000, 'xatol': 1e-12, 'fatol': 1e-12}
    )

    kappa_est, sigma_est = result.x
    n_clusters_est = kappa_est * study_area_m2
    mu_est = n_points / n_clusters_est if n_clusters_est > 0 else float(n_points)

    print(f"Thomas process fit: kappa={kappa_est:.2e} clusters/m², "
          f"sigma={sigma_est/1000:.1f} km, "
          f"~{n_clusters_est:.0f} clusters, ~{mu_est:.1f} loads/cluster")
    return kappa_est, sigma_est, n_clusters_est, mu_est


# ── Step 4: Generate Synthetic Load Locations ─────────────────────────────────

def generate_area_aware_loads(area_stats_df, sigma_fallback_m,
                               boundary_polygon=None, rng=None):
    """
    Generate synthetic large-load locations using area centroids as cluster parents.

    Each area spawns Poisson(NumLoads) offspring points scattered around the
    area centroid using a Gaussian kernel with sigma = MeanSpread_km (or fallback).
    Points outside boundary_polygon are rejected.

    Parameters
    ----------
    area_stats_df : pd.DataFrame
        Must have: AreaName, NumLoads, CentroidLat, CentroidLon, MeanSpread_km
    sigma_fallback_m : float
        Fallback scatter in meters for areas with only 1 load (no spread data).
    boundary_polygon : shapely geometry, optional
        ERCOT boundary — reject points outside this polygon.
    rng : np.random.Generator, optional

    Returns
    -------
    pd.DataFrame with columns: Latitude, Longitude, AreaName, ClusterID
    """
    if rng is None:
        rng = np.random.default_rng(42)

    all_lats, all_lons, all_areas, all_cids = [], [], [], []

    for cid, (_, row) in enumerate(area_stats_df.iterrows()):
        n_offspring = rng.poisson(row['NumLoads'])
        if n_offspring == 0:
            continue

        sigma_km = row['MeanSpread_km'] if row['MeanSpread_km'] > 0 else abs(sigma_fallback_m) / 1000
        sigma_km = max(sigma_km, 1.0)  # floor at 1 km

        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * np.cos(np.radians(row['CentroidLat']))

        for _ in range(n_offspring):
            dx_km  = rng.normal(0, sigma_km)
            dy_km  = rng.normal(0, sigma_km)
            new_lat = row['CentroidLat'] + dy_km / km_per_deg_lat
            new_lon = row['CentroidLon'] + dx_km / km_per_deg_lon

            if boundary_polygon is not None:
                if not boundary_polygon.contains(Point(new_lon, new_lat)):
                    continue

            all_lats.append(new_lat)
            all_lons.append(new_lon)
            all_areas.append(row['AreaName'])
            all_cids.append(cid)

    result = pd.DataFrame({
        'Latitude':  all_lats,
        'Longitude': all_lons,
        'AreaName':  all_areas,
        'ClusterID': all_cids,
    })
    print(f"Generated {len(result)} synthetic large-load locations")
    return result


# ── Step 5: MW Assignment ─────────────────────────────────────────────────────

def assign_load_mw(synthetic_df, reference_loads_gdf, weather_zone_gdf,
                   zone_col='ERCOT_Clim', min_mw=LARGE_LOAD_MW, rng=None):
    """
    Assign MW to synthetic load locations using per-zone lognormal distributions
    fitted to reference case large loads.

    Parameters
    ----------
    synthetic_df : pd.DataFrame
        Synthetic load locations with Latitude, Longitude columns.
    reference_loads_gdf : GeoDataFrame
        Reference loads with LoadMW and zone_col columns (output of build_area_stats).
    weather_zone_gdf : GeoDataFrame
        ERCOT weather zone shapefile.
    zone_col : str
        Column name for weather zone identifier.
    min_mw : float
        MW floor — sampled values below this are clamped up (ERCOT threshold).
    rng : np.random.Generator, optional

    Returns
    -------
    GeoDataFrame with columns: Latitude, Longitude, AreaName, ERCOT_Clim,
                               AssignedMW, FitSource, geometry
    """
    if rng is None:
        rng = np.random.default_rng(42)

    # Spatial join synthetic points to weather zones
    synthetic_gdf = gpd.GeoDataFrame(
        synthetic_df.copy(),
        geometry=gpd.points_from_xy(synthetic_df['Longitude'], synthetic_df['Latitude']),
        crs='EPSG:4326'
    )
    synthetic_gdf = gpd.sjoin(
        synthetic_gdf, weather_zone_gdf[[zone_col, 'geometry']],
        how='left', predicate='within'
    )
    synthetic_gdf = synthetic_gdf.drop(columns=['index_right'], errors='ignore')
    synthetic_gdf = _fill_missing_zone(synthetic_gdf, weather_zone_gdf, zone_col)

    # Fit lognormal per zone from reference loads
    zone_fits = {}
    if zone_col in reference_loads_gdf.columns:
        for zone, grp in reference_loads_gdf.groupby(zone_col):
            mw_vals = grp['LoadMW'].dropna().values
            if len(mw_vals) >= 3:
                s, loc, scale = lognorm.fit(mw_vals, floc=0)
                zone_fits[zone] = (s, loc, scale)

    # Global fallback
    all_mw = reference_loads_gdf['LoadMW'].dropna().values
    if len(all_mw) >= 3:
        s_g, loc_g, scale_g = lognorm.fit(all_mw, floc=0)
    else:
        s_g, loc_g, scale_g = 0.5, 0, 200.0  # reasonable default if no data

    # Sample MW
    assigned_mw, fit_source = [], []
    for _, row in synthetic_gdf.iterrows():
        zone = row.get(zone_col, None)
        if zone in zone_fits:
            s, loc, scale = zone_fits[zone]
            label = zone
        else:
            s, loc, scale = s_g, loc_g, scale_g
            label = 'global'
        mw = float(lognorm.rvs(s, loc=loc, scale=scale, random_state=rng))
        mw = max(mw, min_mw)
        assigned_mw.append(mw)
        fit_source.append(label)

    synthetic_gdf['AssignedMW'] = assigned_mw
    synthetic_gdf['FitSource']  = fit_source

    print(f"\nSynthetic large loads MW assigned: {len(synthetic_gdf)}")
    summary = synthetic_gdf.groupby(zone_col)['AssignedMW'].agg(['count', 'mean', 'max']).round(1)
    print(summary)
    return synthetic_gdf


# ── Validation Plot ───────────────────────────────────────────────────────────

def plot_spatial_validation(ref_loads_df, synthetic_gdf, boundary_polygon=None,
                             weather_zone_gdf=None, zone_col='ERCOT_Clim',
                             r_max_km=200, n_r=80, seed=42):
    """
    Validate synthetic large-load spatial distribution against:
      - Observed (reference case) point pattern
      - Complete Spatial Randomness / Poisson (CSR) simulation

    Produces three panels:
      Panel A — Ripley's L-function: Observed vs Synthetic vs CSR (±envelope)
      Panel B — Nearest-neighbour CDF: Observed vs Synthetic vs CSR
      Panel C — Spatial map: Observed vs Synthetic vs CSR (side-by-side)

    Parameters
    ----------
    ref_loads_df : pd.DataFrame or GeoDataFrame
        Reference large loads with Latitude, Longitude columns.
    synthetic_gdf : pd.DataFrame or GeoDataFrame
        Synthetic large loads with Latitude, Longitude columns.
    boundary_polygon : shapely geometry, optional
        ERCOT boundary — used to draw map outline and constrain CSR simulation.
    weather_zone_gdf : GeoDataFrame, optional
        Weather zones — drawn on map panels if provided.
    zone_col : str
        Column name for weather zone identifier (used for map legend colouring).
    r_max_km : float
        Maximum distance for Ripley's K/L analysis (km).
    n_r : int
        Number of distance bins.
    seed : int
        Random seed for CSR simulation reproducibility.
    """
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from scipy.spatial.distance import pdist, squareform
    from pyproj import Transformer

    rng = np.random.default_rng(seed)

    # ── Helper: compute Ripley's L-function from lat/lon array ────────────────
    def _ripley_L(lats, lons, r_values_m):
        if len(lats) < 3:
            return np.zeros_like(r_values_m)
        from pyproj import Transformer as T
        cLat, cLon = lats.mean(), lons.mean()
        zone_num = int(np.floor((cLon + 180) / 6) + 1)
        epsg = 32600 + zone_num if cLat >= 0 else 32700 + zone_num
        tr = T.from_crs('EPSG:4326', f'EPSG:{epsg}', always_xy=True)
        x, y = tr.transform(lons, lats)
        buf = 10_000
        area = (x.max() - x.min() + 2*buf) * (y.max() - y.min() + 2*buf)
        intensity = len(lats) / area
        coords = np.column_stack([x, y])
        D = squareform(pdist(coords))
        K = np.array([np.sum((D < r) & (D > 0)) / (len(lats) * intensity) for r in r_values_m])
        return np.sqrt(K / np.pi) - r_values_m

    # ── Helper: nearest-neighbour distances (km, haversine) ───────────────────
    def _nn_distances_km(lats, lons):
        if len(lats) < 2:
            return np.array([0.0])
        D = np.array([[_haversine_km(la1, lo1, la2, lo2)
                       for la2, lo2 in zip(lats, lons)]
                      for la1, lo1 in zip(lats, lons)])
        np.fill_diagonal(D, np.inf)
        return D.min(axis=1)

    # ── CSR simulation: uniform random points inside boundary (or bbox) ────────
    ref_lats = np.asarray(ref_loads_df['Latitude'])
    ref_lons = np.asarray(ref_loads_df['Longitude'])
    syn_lats = np.asarray(synthetic_gdf['Latitude'])
    syn_lons = np.asarray(synthetic_gdf['Longitude'])
    n_ref    = len(ref_lats)
    n_syn    = len(syn_lats)

    # Generate CSR with same count as reference, constrained to boundary
    lat_min = min(ref_lats.min(), syn_lats.min())
    lat_max = max(ref_lats.max(), syn_lats.max())
    lon_min = min(ref_lons.min(), syn_lons.min())
    lon_max = max(ref_lons.max(), syn_lons.max())

    csr_lats, csr_lons = [], []
    attempts = 0
    while len(csr_lats) < n_ref and attempts < n_ref * 20:
        attempts += 1
        lat = rng.uniform(lat_min, lat_max)
        lon = rng.uniform(lon_min, lon_max)
        if boundary_polygon is None or boundary_polygon.contains(Point(lon, lat)):
            csr_lats.append(lat)
            csr_lons.append(lon)
    csr_lats = np.array(csr_lats)
    csr_lons = np.array(csr_lons)

    # ── CSR envelope: 19 simulations -> min/max band ──────────────────────────
    r_values_m  = np.linspace(0, r_max_km * 1000, n_r)
    r_values_km = r_values_m / 1000

    n_env = 19
    csr_L_sims = []
    for _ in range(n_env):
        sim_lats, sim_lons = [], []
        att = 0
        while len(sim_lats) < n_ref and att < n_ref * 20:
            att += 1
            lat = rng.uniform(lat_min, lat_max)
            lon = rng.uniform(lon_min, lon_max)
            if boundary_polygon is None or boundary_polygon.contains(Point(lon, lat)):
                sim_lats.append(lat)
                sim_lons.append(lon)
        csr_L_sims.append(_ripley_L(np.array(sim_lats), np.array(sim_lons), r_values_m))

    csr_L_arr = np.array(csr_L_sims) / 1000  # convert to km
    csr_L_lo  = csr_L_arr.min(axis=0)
    csr_L_hi  = csr_L_arr.max(axis=0)
    csr_L_mid = csr_L_arr.mean(axis=0)

    L_ref = _ripley_L(ref_lats, ref_lons, r_values_m) / 1000
    L_syn = _ripley_L(syn_lats, syn_lons, r_values_m) / 1000

    nn_ref = _nn_distances_km(ref_lats, ref_lons)
    nn_syn = _nn_distances_km(syn_lats, syn_lons)
    nn_csr = _nn_distances_km(csr_lats, csr_lons)

    # ── Figure layout ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(20, 13))
    gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.30)

    ax_L   = fig.add_subplot(gs[0, :2])   # Ripley L — wide
    ax_nn  = fig.add_subplot(gs[0, 2])    # NN CDF
    ax_ref = fig.add_subplot(gs[1, 0])    # Map: Observed
    ax_syn = fig.add_subplot(gs[1, 1])    # Map: Synthetic
    ax_csr = fig.add_subplot(gs[1, 2])    # Map: CSR

    COLORS = {'ref': 'steelblue', 'syn': 'tomato', 'csr': 'grey'}

    # ── Panel A: Ripley's L-function ──────────────────────────────────────────
    ax_L.fill_between(r_values_km, csr_L_lo, csr_L_hi,
                      color=COLORS['csr'], alpha=0.25, label='CSR envelope (19 sims)')
    ax_L.plot(r_values_km, csr_L_mid, '--', color=COLORS['csr'],
              lw=1.2, label='CSR mean')
    ax_L.axhline(0, color='black', lw=0.8, linestyle=':')
    ax_L.plot(r_values_km, L_ref, color=COLORS['ref'], lw=2.0,
              label=f'Observed (n={n_ref})')
    ax_L.plot(r_values_km, L_syn, color=COLORS['syn'], lw=2.0,
              label=f'Synthetic (n={n_syn})')
    ax_L.set_xlabel('Distance r  (km)', fontsize=11)
    ax_L.set_ylabel("L(r) − r  (km)", fontsize=11)
    ax_L.set_title("Ripley's L-function  ·  L(r) > 0 = clustering, L(r) < 0 = dispersion",
                   fontsize=11, fontweight='bold')
    ax_L.legend(fontsize=9)
    ax_L.grid(True, linestyle='--', alpha=0.4)

    # ── Panel B: Nearest-Neighbour CDF ────────────────────────────────────────
    for nn, label, color in [
        (nn_ref, f'Observed (n={n_ref})',  COLORS['ref']),
        (nn_syn, f'Synthetic (n={n_syn})', COLORS['syn']),
        (nn_csr, f'CSR (n={len(csr_lats)})', COLORS['csr']),
    ]:
        sv = np.sort(nn)
        ax_nn.plot(sv, np.arange(1, len(sv) + 1) / len(sv),
                   lw=2.0, label=label, color=color)
    ax_nn.set_xlabel('Nearest-neighbour distance  (km)', fontsize=10)
    ax_nn.set_ylabel('Cumulative probability', fontsize=10)
    ax_nn.set_title('NN Distance CDF', fontsize=11, fontweight='bold')
    ax_nn.legend(fontsize=8)
    ax_nn.grid(True, linestyle='--', alpha=0.4)

    # ── Panels C/D/E: Spatial Maps ────────────────────────────────────────────
    map_specs = [
        (ax_ref, ref_lats,  ref_lons,  COLORS['ref'], f'Observed  (n={n_ref})'),
        (ax_syn, syn_lats,  syn_lons,  COLORS['syn'], f'Synthetic  (n={n_syn})'),
        (ax_csr, csr_lats,  csr_lons,  COLORS['csr'], f'CSR / Poisson  (n={len(csr_lats)})'),
    ]
    for ax, lats, lons, color, title in map_specs:
        if weather_zone_gdf is not None:
            weather_zone_gdf.boundary.plot(ax=ax, edgecolor='steelblue',
                                           linewidth=0.6, linestyle='--', alpha=0.5)
        if boundary_polygon is not None:
            import geopandas as _gpd
            _gpd.GeoSeries([boundary_polygon]).boundary.plot(
                ax=ax, edgecolor='black', linewidth=1.0)
        ax.scatter(lons, lats, s=22, color=color, edgecolors='black',
                   linewidths=0.3, alpha=0.75, zorder=5)
        ax.set_title(title, fontsize=10, fontweight='bold')
        ax.set_xlabel('Longitude', fontsize=9)
        ax.set_ylabel('Latitude', fontsize=9)
        ax.grid(True, linestyle='--', linewidth=0.3, alpha=0.4)
        buf_deg = 0.5
        ax.set_xlim(lon_min - buf_deg, lon_max + buf_deg)
        ax.set_ylim(lat_min - buf_deg, lat_max + buf_deg)

    fig.suptitle('ERCOT Large Load Spatial Validation — Observed vs Synthetic vs CSR/Poisson',
                 fontsize=13, fontweight='bold')
    plt.show()


# ── Main Entry Point ───────────────────────────────────────────────────────────

def run_large_load_allocation(saw, weather_zone_gdf, boundary_polygon,
                               fit_thomas=True, sigma_fallback_km=50.0,
                               zone_col='ERCOT_Clim', seed=42):
    """
    Full pipeline: extract -> area stats -> (fit Thomas) -> generate -> assign MW.

    Parameters
    ----------
    saw : SAW
        Open SAW connection to the reference case.
    weather_zone_gdf : GeoDataFrame
        ERCOT weather zone shapefile with ERCOT_Clim + geometry columns.
    boundary_polygon : shapely geometry
        ERCOT boundary polygon for rejecting out-of-bound synthetic points.
    fit_thomas : bool
        If True, fit Thomas Cluster Process to calibrate sigma.
        If False, use sigma_fallback_km as the scatter parameter.
    sigma_fallback_km : float
        Fallback cluster spread in km when fit_thomas=False (default: 50 km).
    zone_col : str
        Column name for weather zone identifier.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    synthetic_assigned : GeoDataFrame
        Synthetic large loads with Latitude, Longitude, AssignedMW, ERCOT_Clim.
    reference_loads_gdf : GeoDataFrame
        Reference large loads with zone assignments (for validation/plotting).
    """
    rng = np.random.default_rng(seed)

    # Step 1: Extract reference large loads
    ref_loads = extract_reference_large_loads(saw)
    if len(ref_loads) == 0:
        raise ValueError("No large loads found in reference case.")

    # Step 2: Build area statistics
    area_stats_df, ref_loads_gdf = build_area_stats(ref_loads, weather_zone_gdf, zone_col)

    # Step 3: Fit Thomas Cluster Process (optional)
    if fit_thomas:
        _, sigma_est, _, _ = fit_thomas_process(ref_loads, len(area_stats_df))
        sigma_fallback_m = sigma_est
    else:
        sigma_fallback_m = sigma_fallback_km * 1000.0
        print(f"Thomas fitting skipped — using sigma_fallback = {sigma_fallback_km} km")

    # Step 4: Generate synthetic locations
    synthetic_locs = generate_area_aware_loads(
        area_stats_df, sigma_fallback_m, boundary_polygon, rng
    )

    # Step 5: Assign MW
    synthetic_assigned = assign_load_mw(
        synthetic_locs, ref_loads_gdf, weather_zone_gdf, zone_col, rng=rng
    )

    return synthetic_assigned, ref_loads_gdf
