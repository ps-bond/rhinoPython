# Using pandas, scrape the ring sizes from the Wikipedia page
# to contain the ring size data.
import pandas as pd

url = 'https://en.wikipedia.org/wiki/Ring_size'

# Mapping from full country names (as found in Wikipedia table columns) to short codes.
# Ensure the keys here exactly match the cleaned column names from the 'Sizes' section of the table.
COUNTRY_NAME_TO_SHORT_CODE_MAPPING = {
    'United Kingdom, Ireland, Australia, South Africa and New Zealand': 'UK',
    'United States, Canada and Mexico': 'USA',
    'East Asia (China, Japan, South Korea), South America': 'Japan',
    'India': 'India',
    'Italy, Spain, Netherlands, Switzerland': 'Italy',
    'France': 'Frances'
}

def fetch_ring_sizes():
    """
    Fetches the ring sizes from the Wikipedia page and returns them as a DataFrame.
    
    Returns:
        pd.DataFrame: A DataFrame containing ring size data for various countries.
    """   
    
    # Read the HTML tables from the Wikipedia page
    tables = pd.read_html(url)
    
    # The specific table we want is usually the first one, but this can vary.
    # Inspect the tables to find the correct one.
    if not tables:
        raise ValueError("No tables found on the page.")
    
    # Assuming the first table contains the ring size data
    # You might need to inspect the list of tables to select the correct one.
    # For example, print len(tables) and tables[0].head(), tables[1].head() etc.
    # For the "Ring_size" page, the main equivalency table is often not the first one.
    # Let's try to find it by looking for a characteristic column name.
    # This is a more robust approach than just taking tables[0].
    
    target_table = None
    # Expected top-level columns in the main ring size equivalency table
    expected_top_level_columns = ['Sizes', 'Inside diameter', 'Inside circumference']

    for i, table_df in enumerate(tables):
        # Defensive copy to avoid SettingWithCopyWarning if we modify columns later
        current_table_df = table_df.copy()

        print(f"\n--- Table {i} ---")
        print(current_table_df.head())

        # Check if a good number of expected columns are present (case-insensitive check)
        # Check if actual top-level column names from the table match expected
        if isinstance(current_table_df.columns, pd.MultiIndex):
            actual_top_level_columns = [str(col).strip().lower() for col in current_table_df.columns.get_level_values(0)]
        else: # Simple Index
            actual_top_level_columns = [str(col).strip().lower() for col in current_table_df.columns]

        found_expected_cols_count = 0
        for expected_col_top in expected_top_level_columns:
            if expected_col_top.lower() in actual_top_level_columns:
                found_expected_cols_count += 1
        
        # Heuristic: if we find at least 2 of our main expected top-level columns
        if found_expected_cols_count >= 2: # e.g., 'Sizes' and 'Inside diameter'
            target_table = current_table_df
            print(f"Selected Table {i} as the target ring size table based on top-level columns.")
            break
            
    if target_table is None:
        print("Could not identify the target ring size table from the page.")
        # Fallback to a specific table index if known, e.g., the third table (index 2)
        # This is based on the observation that the "Equivalency table" is often the 3rd table.
        fallback_index = 2
        if len(tables) > fallback_index:
            print(f"Defaulting to table at index {fallback_index}, but it might not be correct.")
            target_table = tables[fallback_index].copy()
        else:
            raise ValueError("No tables found or target table could not be identified.")

    # Clean column names of the target_table if it's a MultiIndex
    if target_table is not None and isinstance(target_table.columns, pd.MultiIndex):
        new_cols = []
        for col_tuple in target_table.columns.tolist():
            # Ensure all levels are strings and stripped
            new_cols.append(tuple(str(level).strip() for level in col_tuple))
        target_table.columns = pd.MultiIndex.from_tuples(new_cols)
    elif target_table is not None: # Simple Index
        target_table.columns = [str(col).strip() for col in target_table.columns]

    return target_table

def generate_ring_sizes_dict(df, country_col_name):
    """
    Generates a dictionary from the DataFrame containing ring sizes and their corresponding inside diameters
    for a specific country.
    
    Args:
        df (pd.DataFrame): The DataFrame containing ring size data.
        country_col_name (str): The name of the country column under 'Sizes'.

    Returns:
        dict: A dictionary with ring sizes as keys and inside diameters as values.
    """
    ring_sizes_dict = {}
    
    if 'Sizes' not in df.columns or 'Inside diameter' not in df.columns:
        print("Warning: DataFrame missing 'Sizes' or 'Inside diameter' top-level columns.")
        return {}

    sizes_data = df['Sizes']
    diameter_data = df['Inside diameter']

    if country_col_name not in sizes_data.columns:
        print(f"Warning: Country column '{country_col_name}' not found under 'Sizes'.")
        return {}
    
    country_sizes_series = sizes_data[country_col_name].dropna()

    if '(mm)' not in diameter_data.columns:
        print(f"Warning: Diameter column '(mm)' not found under 'Inside diameter'.")
        return {}

    diameter_mm_series = diameter_data['(mm)'].dropna()

    for index, size_value in country_sizes_series.items():
        if index in diameter_mm_series.index:
            diameter_value = diameter_mm_series.loc[index]
            if pd.notna(size_value) and pd.notna(diameter_value):
                try:
                    ring_sizes_dict[str(size_value)] = float(diameter_value)
                except ValueError:
                    print(f"Warning: Could not convert size '{size_value}' or diameter '{diameter_value}' for country '{country_col_name}'. Skipping.")
    return ring_sizes_dict

def generate_python_module_from_data(data_by_country, module_name='ring_data_module'):
    """
    Generates a Python module string from a dictionary of dictionaries containing ring size data.
    
    Args:
        data_by_country (dict): A dictionary where keys are country names and values are
                                 dictionaries of {size: diameter}.
        module_name (str): The name of the module to be created.
        
    Returns:
        str: The generated Python module as a string.
    """
    # Declare the encoding at the top of the module
    module_content = f"# -*- coding: utf-8 -*-\n\n"
    module_content += f"# Module: {module_name}\n\n"
    module_content += f"\"\"\"Generated module containing ring size data by country.\"\"\"\n\n"
    module_content += "# Do not edit this file directly; it is generated by pandas_scraper.py.\n\n"
    module_content += f"# Source: {url}\n\n"
    module_content += "ring_data_by_country = {\n"
    for short_code, country_data in data_by_country.items():
        # Use repr() for keys and string values to ensure proper Python literal generation
        module_content += f"    {repr(short_code)}: {{\n"
        module_content += f"        'full_name': {repr(country_data['full_name'])},\n"
        module_content += f"        'sizes': {{\n"
        if 'sizes' in country_data and isinstance(country_data['sizes'], dict):
            for size, diameter in country_data['sizes'].items():
                module_content += f"            {repr(str(size))}: {diameter},\n"
        else:
            # Handle cases where 'sizes' might be missing or not a dict, though unlikely with current logic
            module_content += "            # No size data available\n"
        module_content += f"        }},\n"  # Closes the 'sizes' dictionary and adds a comma for the 'sizes' entry within its parent (the short_code dict).
        module_content += f"    }},\n"      # Closes the dictionary for the current 'short_code' and adds a comma for this country's entry in the main 'ring_data_by_country' dict.
    module_content += "}\n"
    
    return module_content

def process_ring_data_by_country(ring_sizes_df):
    """
    Processes the ring sizes DataFrame to create a dictionary of ring sizes by country,
    indexed by a short country code, and including the full country name.

    Args:
        ring_sizes_df (pd.DataFrame): The DataFrame containing ring size data.

    Returns:
        dict: A dictionary where keys are country names and values are dictionaries
              of {size: diameter}.
    """
    all_countries_ring_data = {}
    if 'Sizes' in ring_sizes_df.columns and isinstance(ring_sizes_df['Sizes'], pd.DataFrame):
        country_column_names = ring_sizes_df['Sizes'].columns.tolist()
        for country_name in country_column_names:
            country_name_cleaned = country_name.strip()
            print(f"Processing country: {country_name_cleaned}")
            
            country_specific_sizes_dict = generate_ring_sizes_dict(ring_sizes_df, country_name) # Pass original full name
            
            if country_specific_sizes_dict:
                short_code = COUNTRY_NAME_TO_SHORT_CODE_MAPPING.get(country_name_cleaned)
                if short_code:
                    all_countries_ring_data[short_code] = {
                        'full_name': country_name_cleaned,
                        'sizes': country_specific_sizes_dict
                    }
                    print(f"Mapped '{country_name_cleaned}' to short code '{short_code}'. Data included.")
                else:
                    print(f"Warning: No short code mapping found for '{country_name_cleaned}'. This country's data will be skipped. Update COUNTRY_NAME_TO_SHORT_CODE_MAPPING if required.")
            else:
                print(f"No size data generated for {country_name_cleaned}")
    else:
        print("Could not find 'Sizes' sub-columns or 'Sizes' is not structured as expected.")
    return all_countries_ring_data

def main():
    try:
        ring_sizes_df = fetch_ring_sizes()
        print("\nRing Sizes DataFrame (Selected Table):")
        print(ring_sizes_df)
        
        # Display all the column names to verify the structure
        print("\nColumn Names in the DataFrame:")
        print(ring_sizes_df.columns.tolist())
        
        all_countries_ring_data = process_ring_data_by_country(ring_sizes_df)

        if not all_countries_ring_data:
            # This condition might be met if process_ring_data_by_country encounters issues
            # and returns an empty dictionary without raising an error.
            print("No ring data was processed. Exiting.")
            return

        print("\n--- All Ring Sizes Data by Country (Final Structure) ---")
        for short_code, data in all_countries_ring_data.items():
            print(f"\nShort Code: {short_code}")
            print(f"  Full Name: {data.get('full_name', 'N/A')}")
            print(f"  Sizes: {data.get('sizes', {})}")
        
        # Example of accessing the data:
        # target_short_code = 'UK' # Example short code
        # if target_short_code in all_countries_ring_data:
        #     country_info = all_countries_ring_data[target_short_code]
        #     print(f"\nExample: Data for {target_short_code} (Full Name: {country_info.get('full_name', 'N/A')}):")
        #     print(f"  All sizes for {target_short_code}: {country_info.get('sizes', {})}")
        #     # Example: Accessing a specific size for that country (e.g., 'A')
        #     example_size_key = 'A' # Make sure this key actually exists for the chosen country's sizes
        #     if example_size_key in country_info.get('sizes', {}):
        #         print(f"  Size '{example_size_key}' diameter in {target_short_code}: {country_info['sizes'][example_size_key]}")
        #     else:
        #         print(f"  Size '{example_size_key}' not found for {target_short_code}.")
        # else:
        #     print(f"\nExample: Short code '{target_short_code}' not found in processed data.")

        module_content = generate_python_module_from_data(all_countries_ring_data)
        print("\nGenerated Python Module Content:")
        print(module_content)
        # Optionally, you can write this to a .py file
        with open('../ring_sizes.py', 'w', encoding='utf-8') as f:
            f.write(module_content) 
            print("\nPython module 'ring_sizes.py' has been generated successfully.")
        
            
    except pd.errors.ConnectionError as ce:
        print(f"Connection Error: {ce}")            
    except pd.errors.HTTPError as he:
        print(f"HTTP Error: {he}")
    except pd.errors.ParserError:
        print("Error parsing the HTML tables. The structure might have changed.")
    except pd.errors.EmptyDataError:
        print("No data found in the table.")            
    except ValueError as ve:
        print(f"Value Error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")
        
if __name__ == "__main__":
    main()
