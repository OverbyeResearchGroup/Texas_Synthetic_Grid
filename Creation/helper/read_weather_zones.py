import geopandas as gpd
from shapely.geometry import Point


def lat_lon_to_zone(lat, lon):
    """
    Get weather zone name from lat/lon coordinates

    Parameters:
    -----------
    lat : float - Latitude
    lon : float - Longitude

    Returns:
    --------
    str or None - Zone name or None if not found
    """
    # Load shapefile
    shapefile_path = r"D:\Github\Texas_Synthetic_Grid\Creation\input\Shape files\ERCOT_WEATHER_ZONE_modified\ERCOT_WEATHER_ZONE_modified.shp"
    gdf = gpd.read_file(shapefile_path)

    # Convert CRS if needed
    if gdf.crs is None:
        gdf = gdf.set_crs('EPSG:4269')
    if gdf.crs.to_string() != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')

    # Find zone column (try common names)
    zone_col = None
    for col in ['ZONE', 'Zone', 'NAME', 'Name', 'WEATHER_ZONE']:
        if col in gdf.columns:
            zone_col = col
            break

    if zone_col is None:
        zone_col = [c for c in gdf.columns if c != 'geometry'][0]

    # Create point and find matching zone
    point = Point(lon, lat)
    matches = gdf[gdf.geometry.contains(point)]

    return matches.iloc[0][zone_col] if len(matches) > 0 else None