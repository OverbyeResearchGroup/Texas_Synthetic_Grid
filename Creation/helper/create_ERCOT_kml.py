import geopandas as gpd
import fiona
import pandas as pd


def create_ercot_counties_kml(shapefile_path, output_kml='ercot_service_area.kml'):
    """
    Create KML for ERCOT service area counties (blue counties from map)
    """

    # List of all blue counties from the image
    ercot_counties = [
        # Panhandle
        'Oldham', 'Potter', 'Carson', 'Gray', 'Wheeler', 'Roberts',
        'Deaf Smith', 'Randall', 'Armstrong', 'Donley', 'Collingsworth',
        'Parmer', 'Castro', 'Swisher', 'Briscoe', 'Hall', 'Childress',
        'Hale', 'Floyd', 'Motley', 'Cottle',
        'Lubbock', 'Crosby', 'Dickens', 'King', 'Knox',
        'Lynn', 'Garza', 'Kent', 'Stonewall', 'Haskell',
        'Dawson', 'Borden', 'Scurry', 'Fisher', 'Jones',
        'Andrews', 'Martin', 'Howard', 'Mitchell', 'Nolan', 'Taylor', 'Callahan',
        'Loving', 'Winkler', 'Ector', 'Midland', 'Glasscock', 'Sterling', 'Coke', 'Runnels',
        'Ward', 'Crane', 'Upton', 'Reagan', 'Irion', 'Tom Green', 'Concho',
        'Reeves', 'Pecos', 'Crockett', 'Schleicher', 'Menard',
        'Jeff Davis', 'Terrell', 'Sutton', 'Kimble',
        'Culberson',
        'Presidio', 'Brewster', 'Val Verde', 'Edwards', 'Real', 'Kerr', 'Bandera',
        'Kinney', 'Uvalde', 'Medina', 'Bexar',
        'Maverick', 'Zavala', 'Frio', 'Atascosa', 'Wilson',
        'Dimmit', 'La Salle', 'McMullen', 'Live Oak', 'Karnes',
        'Webb', 'Duval', 'Jim Wells', 'Bee',
        'Zapata', 'Jim Hogg', 'Brooks', 'Kenedy',
        'Starr', 'Hidalgo', 'Willacy', 'Cameron',

        # Central/North
        'Shackelford', 'Throckmorton',
        'Hardeman', 'Wilbarger', 'Wichita', 'Clay', 'Montague', 'Cooke', 'Grayson', 'Fannin', 'Lamar', 'Red River',
        'Baylor', 'Archer', 'Jack', 'Wise', 'Denton', 'Collin', 'Hunt', 'Hopkins', 'Delta', 'Franklin',
        'Young', 'Stephens', 'Palo Pinto', 'Parker', 'Tarrant', 'Dallas', 'Rockwall', 'Kaufman', 'Wood', 'Titus',
        'Eastland', 'Erath', 'Hood', 'Johnson', 'Ellis', 'Somervell', 'Smith', 'Rains',
        'Comanche', 'Hamilton', 'Bosque', 'Hill', 'Navarro', 'Freestone', 'Anderson', 'Henderson', 'Van Zandt',
        'Brown', 'Mills', 'Lampasas', 'Coryell', 'McLennan', 'Limestone', 'Leon', 'Houston', 'Cherokee',
        'Coleman', 'McCulloch', 'San Saba', 'Bell', 'Falls', 'Robertson', 'Madison', 'Trinity',
        'Mason', 'Llano', 'Burnet', 'Williamson', 'Milam', 'Brazos', 'Grimes', 'Walker',
        'Gillespie', 'Blanco', 'Travis', 'Bastrop', 'Lee', 'Burleson', 'Washington', 'Montgomery',
        'Kendall', 'Comal', 'Hays', 'Caldwell', 'Fayette', 'Austin', 'Waller',
        'Guadalupe', 'Gonzales', 'Lavaca', 'Colorado', 'Wharton',
        'DeWitt', 'Jackson', 'Matagorda', 'Brazoria',
        'Victoria', 'Goliad', 'Calhoun', 'Refugio',
        'San Patricio', 'Aransas', 'Nueces',

        # East Texas
        'Rusk',
        'Nacogdoches',
        'Angelina',
        'Chambers', 'Harris', 'Galveston', 'Fort Bend',
        
        # Missed
        'Foard', 'Kleberg'
    ]

    print(f"Creating KML for {len(ercot_counties)} ERCOT counties...")

    # Read shapefile
    print("Reading shapefile...")
    gdf = gpd.read_file(shapefile_path)

    print(f"\nShapefile has {len(gdf)} records")
    print(f"Available columns: {gdf.columns.tolist()}")

    # Show sample data from all name-like columns
    print("\n" + "=" * 80)
    print("SAMPLE DATA FROM SHAPEFILE:")
    print("=" * 80)
    name_cols = [col for col in gdf.columns if 'US_Count' in col or 'name' in col.lower()]
    if name_cols:
        print(gdf[name_cols].head(20))

    # Try to identify the best county column
    county_column = 'US_Count_1'  # Based on your previous input

    print(f"\n" + "=" * 80)
    print(f"UNIQUE VALUES IN '{county_column}' (first 30):")
    print("=" * 80)
    unique_values = gdf[county_column].unique()[:30]
    for val in unique_values:
        print(f"  '{val}'")

    # Set CRS to WGS84 (required for KML)
    if gdf.crs is None:
        print("\nNo CRS found. Setting to EPSG:4269 (NAD83)...")
        gdf = gdf.set_crs('EPSG:4269')

    if gdf.crs.to_string() != 'EPSG:4326':
        print(f"Converting from {gdf.crs} to EPSG:4326...")
        gdf = gdf.to_crs('EPSG:4326')

    # Determine the pattern and clean county names
    print("\n" + "=" * 80)
    print("DETERMINING MATCHING PATTERN:")
    print("=" * 80)

    sample_val = str(gdf[county_column].iloc[0])
    print(f"Sample value: '{sample_val}'")

    if ', Texas' in sample_val or ', TX' in sample_val:
        print("Pattern detected: 'County Name, Texas' or 'County Name, TX'")

        def extract_county_name(val):
            if pd.isna(val):
                return ''
            val_str = str(val)
            if ',' in val_str:
                return val_str.split(',')[0].strip().replace(' County', '')
            return val_str.replace(' County', '').strip()

        gdf['clean_county'] = gdf[county_column].apply(extract_county_name)
        county_column = 'clean_county'

    elif ' County' in sample_val:
        print("Pattern detected: 'County Name County'")
        gdf['clean_county'] = gdf[county_column].str.replace(' County', '', regex=False)
        county_column = 'clean_county'

    else:
        print("Pattern: Plain county names")

    print(f"Using column: '{county_column}'")
    print(f"Sample cleaned values: {gdf[county_column].head(10).tolist()}")

    # Match counties
    print("\n" + "=" * 80)
    print("MATCHING COUNTIES:")
    print("=" * 80)

    matched_counties = []
    unmatched_counties = []

    for county in ercot_counties:
        clean_county = county.strip()

        # Try exact match (case-insensitive)
        mask = gdf[county_column].str.lower() == clean_county.lower()

        if gdf[mask].shape[0] > 0:
            matched_counties.append(county)
            print(f"✓ {county}")
        else:
            unmatched_counties.append(county)
            print(f"✗ {county}")

    # Filter GeoDataFrame for matched counties
    mask = gdf[county_column].str.lower().isin([c.lower() for c in matched_counties])
    filtered_gdf = gdf[mask].copy()

    # Get all Texas counties from shapefile
    all_shapefile_counties = set(gdf[county_column].str.strip().tolist())

    # Counties in shapefile but NOT in ERCOT list (the gray counties)
    matched_set = set([c.lower() for c in matched_counties])
    excluded_counties = [c for c in all_shapefile_counties
                         if c.lower() not in matched_set and pd.notna(c) and c != '']
    excluded_counties = sorted(excluded_counties)

    print(f"\n{'=' * 80}")
    print(f"MATCHING SUMMARY:")
    print(f"{'=' * 80}")
    print(f"Total ERCOT counties (from image): {len(ercot_counties)}")
    print(f"Matched in shapefile: {len(matched_counties)}")
    print(f"Not found in shapefile: {len(unmatched_counties)}")
    print(f"Total counties in shapefile: {len(all_shapefile_counties)}")
    print(f"Excluded counties (gray on map): {len(excluded_counties)}")

    if len(unmatched_counties) > 0:
        print(f"\n{'=' * 80}")
        print(f"COUNTIES FROM LIST NOT FOUND IN SHAPEFILE ({len(unmatched_counties)}):")
        print(f"{'=' * 80}")
        for i, county in enumerate(sorted(unmatched_counties), 1):
            print(f"  {i:3d}. {county}")

    print(f"\n{'=' * 80}")
    print(f"COUNTIES EXCLUDED FROM KML ({len(excluded_counties)}):")
    print(f"(These are the gray counties on the map - NOT in ERCOT)")
    print(f"{'=' * 80}")
    for i, county in enumerate(excluded_counties, 1):
        print(f"  {i:3d}. {county}")

    # DISSOLVE: Merge all county polygons into one boundary
    print("\n" + "=" * 80)
    print("DISSOLVING BOUNDARIES...")
    print("=" * 80)
    print("Merging all county polygons into single outer boundary...")

    # Dissolve all geometries into one
    dissolved = filtered_gdf.dissolve()

    print(f"Result: {dissolved.geometry.iloc[0].geom_type}")

    # Create new GeoDataFrame with just the boundary
    boundary_gdf = gpd.GeoDataFrame({
        'Name': ['ERCOT Service Area'],
        'Description': [f'ERCOT service area boundary covering {len(matched_counties)} counties']
    }, geometry=[dissolved.geometry.iloc[0]], crs='EPSG:4326')

    # Export to KML
    print(f"\nExporting to KML...")
    fiona.supported_drivers['KML'] = 'rw'
    boundary_gdf.to_file(output_kml, driver='KML')

    print(f"\n{'=' * 80}")
    print(f"✓ SUCCESS: {output_kml}")
    print(f"  Counties merged: {len(matched_counties)}")
    print(f"  Result: Single boundary polygon")
    print(f"{'=' * 80}")

    if len(matched_counties) == 0:
        print("\n" + "!" * 80)
        print("ERROR: No counties matched!")
        print("Please check the county name format in your shapefile.")
        print("!" * 80)
        return None

    # # Export to KML
    # print(f"\n{'=' * 80}")
    # print(f"EXPORTING TO KML...")
    # print(f"{'=' * 80}")
    # fiona.supported_drivers['KML'] = 'rw'
    # filtered_gdf.to_file(output_kml, driver='KML')

    print(f"\n{'=' * 80}")
    print(f"✓ SUCCESS: {output_kml}")
    print(f"  Counties included: {len(filtered_gdf)}")
    print(f"{'=' * 80}")

    # Save summary to text file
    summary_file = output_kml.replace('.kml', '_summary.txt')
    with open(summary_file, 'w') as f:
        f.write("ERCOT COUNTIES KML EXPORT SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total ERCOT counties (from image): {len(ercot_counties)}\n")
        f.write(f"Matched in shapefile: {len(matched_counties)}\n")
        f.write(f"Not found in shapefile: {len(unmatched_counties)}\n")
        f.write(f"Total counties in shapefile: {len(all_shapefile_counties)}\n")
        f.write(f"Excluded counties (not in ERCOT): {len(excluded_counties)}\n\n")

        f.write("=" * 80 + "\n")
        f.write("COUNTIES INCLUDED IN KML (ERCOT Service Area):\n")
        f.write("=" * 80 + "\n")
        for i, county in enumerate(sorted(matched_counties), 1):
            f.write(f"  {i:3d}. {county}\n")

        if unmatched_counties:
            f.write("\n" + "=" * 80 + "\n")
            f.write("COUNTIES FROM LIST NOT FOUND IN SHAPEFILE:\n")
            f.write("=" * 80 + "\n")
            for i, county in enumerate(sorted(unmatched_counties), 1):
                f.write(f"  {i:3d}. {county}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("COUNTIES EXCLUDED FROM KML (NOT in ERCOT):\n")
        f.write("=" * 80 + "\n")
        for i, county in enumerate(excluded_counties, 1):
            f.write(f"  {i:3d}. {county}\n")

    print(f"\nSummary saved to: {summary_file}")

    return filtered_gdf


# Usage
if __name__ == "__main__":
    # Option 1: If you have the Texas counties shapefile
    gdf = create_ercot_counties_kml(
        shapefile_path='D:\\Github\\Texas_Synthetic_Grid\\Creation\\input\\Shape files\\ERCOT\\Texas_Counties.shp',
        output_kml='D:\\Github\\Texas_Synthetic_Grid\\Creation\\input\\ercot_service_area.kml'
    )

    # Option 2: Download and use in one go
    # Uncomment below if you need to download first
    """
    import urllib.request
    import zipfile

    print("Downloading Texas county shapefile...")
    url = "https://www2.census.gov/geo/tiger/TIGER2022/COUNTY/tl_2022_us_county.zip"
    urllib.request.urlretrieve(url, "counties.zip")

    with zipfile.ZipFile("counties.zip", 'r') as zip_ref:
        zip_ref.extractall("counties")

    gdf = create_ercot_counties_kml(
        shapefile_path='counties/tl_2022_us_county.shp',
        output_kml='ercot_service_area.kml'
    )
    """