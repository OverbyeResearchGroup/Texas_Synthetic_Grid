# Created by: Sanjana Kunkolienkar
# Date: 10 March 2026

# What this file does?
# Read texas shape file with counties
# Create a polygon for each county
# Read GIS gen csv
# For each gen, look up county and add arbitrarily lat lon to these gen.

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import random
import numpy as np


def generate_random_point_in_polygon(polygon, max_attempts=1000):
    """
    Generate a random point inside a polygon.
    Uses a bounding box approach with rejection sampling.
    """
    minx, miny, maxx, maxy = polygon.bounds

    for _ in range(max_attempts):
        # Generate random point within bounding box
        random_point = Point(
            random.uniform(minx, maxx),
            random.uniform(miny, maxy)
        )

        # Check if point is inside the polygon
        if polygon.contains(random_point):
            return random_point.y, random_point.x  # Return as (latitude, longitude)

    # If we couldn't find a point, return the centroid
    centroid = polygon.centroid
    return centroid.y, centroid.x


def explore_shapefile(shapefile_path):
    """
    Explore and display information about the shapefile
    """
    print("=" * 60)
    print("EXPLORING SHAPEFILE")
    print("=" * 60)

    # Read the shapefile
    gdf = gpd.read_file(shapefile_path)

    # Basic info
    print(f"\nNumber of records: {len(gdf)}")
    print(f"CRS: {gdf.crs}")
    print(f"\nColumn names:")
    print(gdf.columns.tolist())

    # Show all columns with sample data
    print("\n" + "=" * 60)
    print("SAMPLE DATA (first 5 rows):")
    print("=" * 60)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 50)
    print(gdf.head())

    # Show unique values for likely name columns
    print("\n" + "=" * 60)
    print("UNIQUE VALUES IN KEY COLUMNS:")
    print("=" * 60)

    name_columns = [col for col in gdf.columns if any(keyword in col.upper()
                                                      for keyword in ['NAME', 'COUNTY', 'AREA', 'REGION', 'DISTRICT'])]

    for col in name_columns:
        unique_vals = gdf[col].unique()
        print(f"\n{col}: ({len(unique_vals)} unique values)")
        print(unique_vals[:20])  # Show first 20
        if len(unique_vals) > 20:
            print(f"... and {len(unique_vals) - 20} more")

    return gdf

def main():
    # Read the CSV file with proper encoding handling
    print("Reading CSV file...")

    encodings_to_try = ['cp1252', 'latin-1', 'iso-8859-1', 'utf-8']
    df = None

    for encoding in encodings_to_try:
        try:

            df = pd.read_csv("D:\\Github\\Texas_Synthetic_Grid\\Creation\\input\\GIS_Plant_madeup.csv",
                             encoding='cp1252')
            print(f"Successfully read CSV with {encoding} encoding")
            break
        except UnicodeDecodeError:
            continue

    if df is None:
        raise ValueError("Could not read CSV with any common encoding")

    # Read the shapefile
    print("Reading shapefile...")
    gdf = gpd.read_file(
        'D:\\Github\\Texas_Synthetic_Grid\\Creation\\input\\Shape files\\ERCOT\\Texas_Counties.shp')
    # Show unique counties in CSV
    print("\n" + "=" * 60)
    print("COUNTIES IN YOUR CSV FILE:")
    print("=" * 60)
    print(df['County'].unique())
    print(f"\nTotal unique counties: {df['County'].nunique()}")

    # Explore the shapefile
    gdf = explore_shapefile('D:\\Github\\Texas_Synthetic_Grid\\Creation\\input\\Shape files\\ERCOT\\Texas_Counties.shp')


    # Display available columns in shapefile
    print("\nShapefile columns:", gdf.columns.tolist())
    print("\nFirst few rows of shapefile:")
    print(gdf.head())

    # Check and handle CRS
    print(f"\nOriginal CRS: {gdf.crs}")

    if gdf.crs is None:
        # Shapefile has no CRS defined
        # For Texas shapefiles (tl_2022_48_*), try common projections
        print("No CRS found. Setting to EPSG:4269 (NAD83)...")
        gdf = gdf.set_crs('EPSG:4269')
        print(f"CRS set to: {gdf.crs}")

    # Convert to WGS84 for lat/lon if needed
    if gdf.crs.to_string() != 'EPSG:4326':
        print(f"Converting from {gdf.crs} to EPSG:4326...")
        gdf = gdf.to_crs('EPSG:4326')
        print("Conversion complete")

    # Try to identify the county column
    county_column = None
    possible_county_columns = ['COUNTY', 'County', 'NAME', 'NAMELSAD', 'COUNTYNS', 'COUSUBNS']

    for col in possible_county_columns:
        if col in gdf.columns:
            county_column = col
            break

    if county_column is None:
        print("\nAvailable columns in shapefile:", gdf.columns.tolist())
        county_column = input("Enter the column name for county: ")

    print(f"\nUsing '{county_column}' as county column")
    print(f"Unique values in {county_column}:")
    print(gdf[county_column].unique()[:10])  # Show first 10

    # Process each row in the CSV
    print("\nGenerating random coordinates for each plant...")
    for idx, row in df.iterrows():
        county_name = row['County']

        if pd.isna(county_name):
            print(f"Row {idx}: No county specified, skipping...")
            continue

        # Try to find matching county in shapefile
        clean_county = str(county_name).strip()

        # Try exact match first
        matching_counties = gdf[gdf[county_column].str.contains(clean_county, case=False, na=False)]

        if len(matching_counties) == 0:
            print(f"Row {idx}: County '{county_name}' not found in shapefile")
            continue

        if len(matching_counties) > 1:
            print(f"Row {idx}: Multiple matches found for '{county_name}', using first match")

        county_polygon = matching_counties.iloc[0].geometry

        # Handle MultiPolygon
        if county_polygon.geom_type == 'MultiPolygon':
            county_polygon = max(county_polygon.geoms, key=lambda p: p.area)

        # Generate random point inside the polygon
        lat, lon = generate_random_point_in_polygon(county_polygon)

        # Update the dataframe
        df.at[idx, 'Latitude'] = lat
        df.at[idx, 'Longitude'] = lon

        print(f"Row {idx}: Plant '{row['Plant Code']}' in {county_name} -> ({lat:.6f}, {lon:.6f})")

    # Save the updated CSV
    output_filename = 'GIS_Plant_madeup_updated.csv'
    df.to_csv(output_filename, index=False)
    print(f"\nUpdated CSV saved as: {output_filename}")

    # Display summary
    filled_count = df['Latitude'].notna().sum()
    total_count = len(df)
    print(f"\nSummary: {filled_count}/{total_count} plants have coordinates assigned")

if __name__ == "__main__":
    main()