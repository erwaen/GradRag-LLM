import pandas as pd
import re
import requests
import io

# Define URLs for the CSV files
TURING_URL = "https://csrankings.org/turing.csv"
ACMFELLOW_URL = "https://csrankings.org/acm-fellows.csv"
AUTHOR_URL = "https://csrankings.org/csrankings.csv"
AUTHOR_INFO_URL = "https://csrankings.org/generated-author-info.csv"
COUNTRY_INFO_URL = "https://csrankings.org/country-info.csv"

# Regex to match name and note like in the JS code
NAME_MATCHER = re.compile(r"^(.*)\s+\[(.*?)\]$")

def download_csv_to_dataframe(url):
    """Downloads CSV from a URL and returns a pandas DataFrame."""
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        # Use io.StringIO to treat the string content as a file for pandas
        csv_content = io.StringIO(response.text)
        df = pd.read_csv(csv_content, header=0)
        print(f"Successfully downloaded and parsed CSV from {url}")
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error downloading CSV from {url}: {e}")
        return None
    except pd.errors.EmptyDataError:
        print(f"Error: No data or empty CSV found at {url}")
        return None
    except Exception as e:
        print(f"Error processing CSV from {url}: {e}")
        return None

def load_turing_data(url=TURING_URL):
    """Loads Turing award data from a URL."""
    df = download_csv_to_dataframe(url)
    if df is None:
        return {}
    try:
        # Convert to dictionary {name: year} like the JS code
        turing_data = df.set_index("name")["year"].to_dict()
        print(f"Successfully processed Turing data from {url}")
        return turing_data
    except KeyError as e:
        print(f"Error processing Turing data: Missing expected column {e}")
        return {}
    except Exception as e:
        print(f"Error processing Turing data from {url}: {e}")
        return {}

def load_acm_fellow_data(url=ACMFELLOW_URL):
    """Loads ACM Fellow data from a URL."""
    df = download_csv_to_dataframe(url)
    if df is None:
        return {}
    try:
        # Convert to dictionary {name: year} like the JS code
        acm_fellow_data = df.set_index("name")["year"].to_dict()
        print(f"Successfully processed ACM Fellow data from {url}")
        return acm_fellow_data
    except KeyError as e:
        print(f"Error processing ACM Fellow data: Missing expected column {e}")
        return {}
    except Exception as e:
        print(f"Error processing ACM Fellow data from {url}: {e}")
        return {}

def load_author_info(url=AUTHOR_URL):
    """Loads author info (homepage, scholarid) from URL and extracts notes."""
    homepages = {}
    scholar_info = {}
    notes = {}
    # Need to prevent pandas from interpreting NA/NaN etc. as NaN
    # Use keep_default_na=False and handle potential empty strings
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_content = io.StringIO(response.text)
        # Read CSV specifically for this function to handle na_values correctly
        df = pd.read_csv(csv_content, header=0, keep_default_na=False)
        print(f"Successfully downloaded and parsed CSV from {url}")
        
        for index, row in df.iterrows():
            name = str(row["name"]).strip() # Ensure name is string
            match = NAME_MATCHER.match(name)
            if match:
                name = match.group(1).strip()
                notes[name] = match.group(2)
            
            if name:
                homepages[name] = str(row["homepage"]) # Ensure string
                scholar_info[name] = str(row["scholarid"]) # Ensure string
                
        print(f"Successfully processed author info from {url}")
        return homepages, scholar_info, notes
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading CSV from {url}: {e}")
        return {}, {}, {}
    except pd.errors.EmptyDataError:
        print(f"Error: No data or empty CSV found at {url}")
        return {}, {}, {}
    except KeyError as e:
        print(f"Error processing Author info: Missing expected column {e}")
        return {}, {}, {}
    except Exception as e:
        print(f"Error processing author info from {url}: {e}")
        return {}, {}, {}

def load_authors_publications(url=AUTHOR_INFO_URL):
    """Loads author publication data from the generated CSV file URL."""
    df = download_csv_to_dataframe(url)
    if df is None:
        return pd.DataFrame() # Return empty DataFrame on error
    print(f"Successfully processed author publications from {url}")
    # Return the DataFrame directly
    return df

def load_country_info(url=COUNTRY_INFO_URL):
    """Loads country/region information for institutions from URL."""
    country_info = {}
    country_abbrv = {}
    df = download_csv_to_dataframe(url)
    if df is None:
        return {}, {}
    try:
        for index, row in df.iterrows():
            institution = row["institution"]
            country_info[institution] = row["region"]
            country_abbrv[institution] = row["countryabbrv"]
        print(f"Successfully processed country info from {url}")
        return country_info, country_abbrv
    except KeyError as e:
        print(f"Error processing Country info: Missing expected column {e}")
        return {}, {}
    except Exception as e:
        print(f"Error processing country info from {url}: {e}")
        return {}, {}

if __name__ == "__main__":
    print("--- Loading CSRankings Data via HTTP ---")
    
    # Load data using the functions (now fetching from URLs)
    turing_awards = load_turing_data()
    acm_fellows = load_acm_fellow_data()
    homepages, scholar_ids, author_notes = load_author_info()
    author_publications = load_authors_publications()
    country_regions, country_abbreviations = load_country_info()
    
    print("\n--- Data Loading Summary ---")
    print(f"Loaded {len(turing_awards)} Turing Award records.")
    print(f"Loaded {len(acm_fellows)} ACM Fellow records.")
    print(f"Loaded info for {len(homepages)} authors (homepages, scholar IDs, notes).")
    # Check if author_publications is a DataFrame before getting len
    pub_count = len(author_publications) if isinstance(author_publications, pd.DataFrame) else 0
    print(f"Loaded {pub_count} author publication records.")
    print(f"Loaded country info for {len(country_regions)} institutions.")

    # Example: Print first 5 publication records
    if isinstance(author_publications, pd.DataFrame) and not author_publications.empty:
        print("\n--- First 5 Author Publication Records ---")
        print(author_publications.head())
    
    # Example: Print info for the first 15 authors if available
    print("\n--- Example Author Data (First 15) ---")
    for i in range(15):
        if i < len(homepages):
            example_author = list(homepages.keys())[i]
            print(f"\n--- Author {i+1}: {example_author} ---")
            print(f"  Homepage: {homepages.get(example_author)}")
            print(f"  Scholar ID: {scholar_ids.get(example_author)}")
            print(f"  Note: {author_notes.get(example_author)}")
            # Optional: You could also filter author_publications here for this author
        else:
            print(f"\nNo more authors to display (only {len(homepages)} found).")
            break

