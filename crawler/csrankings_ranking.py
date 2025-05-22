import pandas as pd
import re
import requests
import io
import math
from collections import defaultdict

# --- Configuration & Data Definitions ---

# Define URLs for the CSV files
TURING_URL = "https://csrankings.org/turing.csv"
ACMFELLOW_URL = "https://csrankings.org/acm-fellows.csv"
AUTHOR_URL = "https://csrankings.org/csrankings.csv"
AUTHOR_INFO_URL = "https://csrankings.org/generated-author-info.csv"
COUNTRY_INFO_URL = "https://csrankings.org/country-info.csv"

# Regex to match name and note like in the JS code
NAME_MATCHER = re.compile(r"^(.*)\s+\[(.*?)\]$")

# Area definitions based on csrankings.js
AREA_MAP = [
    {"area": "ai", "title": "AI"},
    {"area": "aaai", "title": "AI"},
    {"area": "ijcai", "title": "AI"},
    {"area": "vision", "title": "Vision"},
    {"area": "cvpr", "title": "Vision"},
    {"area": "eccv", "title": "Vision"},
    {"area": "iccv", "title": "Vision"},
    {"area": "mlmining", "title": "ML"},
    {"area": "icml", "title": "ML"},
    {"area": "kdd", "title": "ML"},
    {"area": "iclr", "title": "ML"},
    {"area": "nips", "title": "ML"},
    {"area": "nlp", "title": "NLP"},
    {"area": "acl", "title": "NLP"},
    {"area": "emnlp", "title": "NLP"},
    {"area": "naacl", "title": "NLP"},
    {"area": "inforet", "title": "Web+IR"},
    {"area": "sigir", "title": "Web+IR"},
    {"area": "www", "title": "Web+IR"},
    {"area": "arch", "title": "Arch"},
    {"area": "asplos", "title": "Arch"},
    {"area": "isca", "title": "Arch"},
    {"area": "micro", "title": "Arch"},
    {"area": "hpca", "title": "Arch"},
    {"area": "comm", "title": "Networks"},
    {"area": "sigcomm", "title": "Networks"},
    {"area": "nsdi", "title": "Networks"},
    {"area": "sec", "title": "Security"},
    {"area": "ccs", "title": "Security"},
    {"area": "oakland", "title": "Security"},
    {"area": "usenixsec", "title": "Security"},
    {"area": "ndss", "title": "Security"},
    {"area": "pets", "title": "Security"},
    {"area": "mod", "title": "DB"},
    {"area": "sigmod", "title": "DB"},
    {"area": "vldb", "title": "DB"},
    {"area": "icde", "title": "DB"}, # next tier
    {"area": "pods", "title": "DB"}, # next tier
    {"area": "hpc", "title": "HPC"},
    {"area": "sc", "title": "HPC"},
    {"area": "hpdc", "title": "HPC"},
    {"area": "ics", "title": "HPC"},
    {"area": "mobile", "title": "Mobile"},
    {"area": "mobicom", "title": "Mobile"},
    {"area": "mobisys", "title": "Mobile"},
    {"area": "sensys", "title": "Mobile"},
    {"area": "metrics", "title": "Metrics"},
    {"area": "imc", "title": "Metrics"},
    {"area": "sigmetrics", "title": "Metrics"},
    {"area": "ops", "title": "OS"},
    {"area": "sosp", "title": "OS"},
    {"area": "osdi", "title": "OS"},
    {"area": "fast", "title": "OS"}, # next tier
    {"area": "usenixatc", "title": "OS"}, # next tier
    {"area": "eurosys", "title": "OS"},
    {"area": "pldi", "title": "PL"},
    {"area": "popl", "title": "PL"},
    {"area": "icfp", "title": "PL"}, # next tier
    {"area": "oopsla", "title": "PL"}, # next tier
    {"area": "plan", "title": "PL"},
    {"area": "soft", "title": "SE"},
    {"area": "fse", "title": "SE"},
    {"area": "icse", "title": "SE"},
    {"area": "ase", "title": "SE"}, # next tier
    {"area": "issta", "title": "SE"}, # next tier
    {"area": "act", "title": "Theory"},
    {"area": "focs", "title": "Theory"},
    {"area": "soda", "title": "Theory"},
    {"area": "stoc", "title": "Theory"},
    {"area": "crypt", "title": "Crypto"},
    {"area": "crypto", "title": "Crypto"},
    {"area": "eurocrypt", "title": "Crypto"},
    {"area": "log", "title": "Logic"},
    {"area": "cav", "title": "Logic"},
    {"area": "lics", "title": "Logic"},
    {"area": "graph", "title": "Graphics"},
    {"area": "siggraph", "title": "Graphics"},
    {"area": "siggraph-asia", "title": "Graphics"},
    {"area": "eurographics", "title": "Graphics"},
    {"area": "chi", "title": "HCI"},
    {"area": "chiconf", "title": "HCI"},
    {"area": "ubicomp", "title": "HCI"},
    {"area": "uist", "title": "HCI"},
    {"area": "robotics", "title": "Robotics"},
    {"area": "icra", "title": "Robotics"},
    {"area": "iros", "title": "Robotics"},
    {"area": "rss", "title": "Robotics"},
    {"area": "bio", "title": "Comp. Bio"},
    {"area": "ismb", "title": "Comp. Bio"},
    {"area": "recomb", "title": "Comp. Bio"},
    {"area": "da", "title": "EDA"},
    {"area": "dac", "title": "EDA"},
    {"area": "iccad", "title": "EDA"},
    {"area": "bed", "title": "Embedded"},
    {"area": "emsoft", "title": "Embedded"},
    {"area": "rtas", "title": "Embedded"},
    {"area": "rtss", "title": "Embedded"},
    {"area": "visualization", "title": "Visualization"},
    {"area": "vis", "title": "Visualization"},
    {"area": "vr", "title": "Visualization"},
    {"area": "ecom", "title": "ECom"},
    {"area": "ec", "title": "ECom"},
    {"area": "wine", "title": "ECom"},
    {"area": "csed", "title": "CSEd"},
    {"area": "sigcse", "title": "CSEd"}
]

AI_AREAS = ["ai", "vision", "mlmining", "nlp", "inforet"]
SYSTEMS_AREAS = ["arch", "comm", "sec", "mod", "da", "bed", "hpc", "mobile", "metrics", "ops", "plan", "soft"]
THEORY_AREAS = ["act", "crypt", "log"]
INTERDISCIPLINARY_AREAS = ["bio", "graph", "csed", "ecom", "chi", "robotics", "visualization"]

# Build derived area structures
AREAS = [item["area"] for item in AREA_MAP]
AREA_TITLES = {item["area"]: item["title"] for item in AREA_MAP}

# Parent map (conference -> area)
PARENT_MAP = {item["area"]: item["title"] for item in AREA_MAP if item["area"] != item["title"].lower().replace("+", "").replace(".", "")}

# Top-level areas (those that are titles)
TOP_LEVEL_AREAS = {item["title"].lower().replace("+", "").replace(".", ""): item["title"] for item in AREA_MAP}
TOP_LEVEL_AREA_KEYS = list(TOP_LEVEL_AREAS.keys())

# Next tier conferences (used for exclusion in some counts)
NEXT_TIER = {
    "icde": True, "pods": True, "fast": True, "usenixatc": True,
    "icfp": True, "oopsla": True, "ase": True, "issta": True
}

# Top tier areas (excluding next tier)
TOP_TIER_AREAS = {area: True for area in AREAS if area not in NEXT_TIER}

# Map conferences to their top-level area
CONF_TO_TOP_AREA = {conf: AREA_TITLES[conf].lower().replace("+", "").replace(".", "") 
                    for conf in PARENT_MAP}

# --- Data Loading Functions (Modified for Error Handling) ---

def download_csv_to_dataframe(url):
    """Downloads CSV from a URL and returns a pandas DataFrame."""
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
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
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_content = io.StringIO(response.text)
        df = pd.read_csv(csv_content, header=0, keep_default_na=False)
        print(f"Successfully downloaded and parsed CSV from {url}")
        
        for index, row in df.iterrows():
            name = str(row["name"]).strip()
            match = NAME_MATCHER.match(name)
            if match:
                name = match.group(1).strip()
                notes[name] = match.group(2)
            
            if name:
                homepages[name] = str(row["homepage"])
                scholar_info[name] = str(row["scholarid"])
                
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
        return pd.DataFrame()
    # Ensure correct types
    try:
        df["year"] = pd.to_numeric(df["year"])
        df["count"] = pd.to_numeric(df["count"])
        df["adjustedcount"] = pd.to_numeric(df["adjustedcount"])
    except KeyError as e:
        print(f"Error processing Author Publications: Missing expected column {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error converting types in Author Publications: {e}")
        # Return df anyway, maybe calculations fail later
        
    print(f"Successfully processed author publications from {url}")
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

# --- Ranking Logic Functions ---

def is_in_region(dept, target_region, country_regions, country_abbreviations):
    """Checks if a department is in the target region."""
    dept_region = country_regions.get(dept)
    dept_abbrv = country_abbreviations.get(dept)

    if target_region == "us":
        return dept not in country_regions
    elif target_region == "northamerica":
        # US (not in country_regions) or Canada
        return dept not in country_regions or dept_region == "canada"
    elif target_region == "world":
        return True
    elif target_region in ["europe", "asia", "australasia", "southamerica", "africa", "canada"]:
        return dept_region == target_region
    else: # Specific country abbreviation
        return dept_abbrv == target_region

def _filter_publications(author_publications_df, selected_areas, start_year, end_year):
    """Helper function to filter publications by area and year."""
    if author_publications_df.empty:
        return pd.DataFrame()
        
    valid_areas = {area for area in selected_areas if area in TOP_LEVEL_AREA_KEYS}
    if not valid_areas:
        print("Warning: No valid top-level areas selected.")
        return pd.DataFrame()

    # Filter by year first
    filtered_df = author_publications_df[
        (author_publications_df["year"] >= start_year) &
        (author_publications_df["year"] <= end_year)
    ].copy()

    # Map publication area (conference) to top-level area
    filtered_df["top_area"] = filtered_df["area"].map(CONF_TO_TOP_AREA)
    
    # Keep only publications in selected top-level areas
    filtered_df = filtered_df[filtered_df["top_area"].isin(valid_areas)]
    
    return filtered_df, valid_areas

def calculate_ranking(author_publications_df, country_regions, country_abbreviations, 
                      selected_areas, start_year, end_year, target_region="world"):
    """Calculates institution rankings based on selected criteria."""
    
    filtered_df, valid_areas = _filter_publications(author_publications_df, selected_areas, start_year, end_year)

    if filtered_df.empty:
        print(f"Warning: No publications found for selected areas {selected_areas} between {start_year}-{end_year}.")
        return pd.DataFrame()

    # Aggregate adjusted counts per institution per top-level area & count faculty
    inst_area_counts = defaultdict(lambda: defaultdict(float))
    inst_faculty_count = defaultdict(int)
    inst_faculty_names = defaultdict(set)

    for _, row in filtered_df.iterrows():
        dept = row["dept"]
        name = row["name"]
        top_area = row["top_area"]
        adj_count = row["adjustedcount"]
        
        # Filter by region
        if not is_in_region(dept, target_region, country_regions, country_abbreviations):
            continue
            
        inst_area_counts[dept][top_area] += adj_count
        
        if name not in inst_faculty_names[dept]:
            inst_faculty_names[dept].add(name)
            inst_faculty_count[dept] += 1

    if not inst_area_counts:
        print(f"Warning: No institutions found matching the region ",
              f"\"{target_region}\" with publications in selected areas/years.")
        return pd.DataFrame()

    # Calculate geometric mean score for each institution
    num_selected_areas = len(valid_areas)
    inst_scores = {}
    for dept, area_counts in inst_area_counts.items():
        product = 1.0
        for area in valid_areas:
            product *= (area_counts.get(area, 0.0) + 1.0)
        
        if num_selected_areas > 0:
            geo_mean = math.pow(product, 1.0 / num_selected_areas)
            inst_scores[dept] = geo_mean
        else:
            inst_scores[dept] = 0.0

    # Create ranked DataFrame
    ranked_list = sorted(inst_scores.items(), key=lambda item: item[1], reverse=True)
    
    results = []
    current_rank = 0
    last_score = float("inf")
    tie_count = 1
    
    for i, (dept, score) in enumerate(ranked_list):
        if score < last_score:
            current_rank += tie_count
            tie_count = 1
        else:
            tie_count += 1
            
        last_score = score
        
        results.append({
            "Rank": current_rank,
            "Institution": dept,
            "Score": round(score, 1),
            "Faculty Count": inst_faculty_count.get(dept, 0)
        })
        
    ranked_df = pd.DataFrame(results)
    return ranked_df

def get_ranked_professors(institution_name, author_publications_df, 
                          selected_areas, start_year, end_year):
    """Gets a ranked list of professors for a specific institution based on criteria."""
    
    filtered_df, valid_areas = _filter_publications(author_publications_df, selected_areas, start_year, end_year)

    if filtered_df.empty:
        print(f"Warning: No publications found for selected areas {selected_areas} between {start_year}-{end_year}.")
        return pd.DataFrame()
        
    # Filter for the specific institution
    inst_df = filtered_df[filtered_df["dept"] == institution_name].copy()
    
    if inst_df.empty:
        print(f"Warning: No publications found for institution ",
              f"\"{institution_name}\" with selected areas/years.")
        return pd.DataFrame()
        
    # Aggregate counts per professor
    prof_counts = defaultdict(lambda: {"total_count": 0, "adj_count": 0.0})
    for _, row in inst_df.iterrows():
        name = row["name"]
        prof_counts[name]["total_count"] += row["count"]
        prof_counts[name]["adj_count"] += row["adjustedcount"]
        
    # Create list of professors with their counts
    prof_list = [
        {
            "Professor": name,
            "Pubs": data["total_count"],
            "Adj Pubs": round(data["adj_count"], 1)
        }
        for name, data in prof_counts.items()
    ]
    
    # Sort according to JS logic: Pubs (desc), Adj Pubs (desc), Name (asc)
    # Note: Python's sort is stable, so we can sort multiple times.
    # Sort by name ascending
    prof_list.sort(key=lambda x: x["Professor"])
    # Sort by adjusted count descending
    prof_list.sort(key=lambda x: x["Adj Pubs"], reverse=True)
    # Sort by total count descending (this is the primary sort key)
    prof_list.sort(key=lambda x: x["Pubs"], reverse=True)
    
    ranked_prof_df = pd.DataFrame(prof_list)
    return ranked_prof_df

# --- Main Execution --- 

if __name__ == "__main__":
    print("--- Loading CSRankings Data via HTTP ---")
    
    # Load data using the functions
    turing_awards = load_turing_data()
    acm_fellows = load_acm_fellow_data()
    homepages, scholar_ids, author_notes = load_author_info()
    author_publications = load_authors_publications()
    country_regions, country_abbreviations = load_country_info()
    
    print("\n--- Data Loading Summary ---")
    print(f"Loaded {len(turing_awards)} Turing Award records.")
    print(f"Loaded {len(acm_fellows)} ACM Fellow records.")
    print(f"Loaded info for {len(homepages)} authors (homepages, scholar IDs, notes).")
    pub_count = len(author_publications) if isinstance(author_publications, pd.DataFrame) else 0
    print(f"Loaded {pub_count} author publication records.")
    print(f"Loaded country info for {len(country_regions)} institutions.")

    # --- Example Institution Ranking Calculation ---
    print("\n--- Example Ranking: AI Areas (2012-2024, World) ---")
    
    # Define parameters for ranking
    selected_ranking_areas = [area for area in TOP_LEVEL_AREA_KEYS if area in AI_AREAS] 
    start_ranking_year = 2015
    end_ranking_year = 2025
    ranking_region = "world" # Options: "us", "europe", "asia", "northamerica", "australasia", "southamerica", "africa", "world", or country abbrv like "ca", "cn", "gb"

    ranked_institutions = pd.DataFrame() # Initialize empty DataFrame
    if not author_publications.empty:
        ranked_institutions = calculate_ranking(
            author_publications,
            country_regions,
            country_abbreviations,
            selected_areas=selected_ranking_areas,
            start_year=start_ranking_year,
            end_year=end_ranking_year,
            target_region=ranking_region
        )

        if not ranked_institutions.empty:
            print(f"Ranking based on areas: {selected_ranking_areas}, Years: {start_ranking_year}-{end_ranking_year}, Region: {ranking_region}")
            print(ranked_institutions.head(20).to_string(index=False))
            
            # --- Example Professor Ranking for Top Institution ---
            top_institution_name = ranked_institutions.iloc[0]["Institution"]
            print(f"\n--- Example Professor Ranking for: {top_institution_name} (AI Areas, 2012-2024) ---")
            
            ranked_profs = get_ranked_professors(
                institution_name=top_institution_name,
                author_publications_df=author_publications,
                selected_areas=selected_ranking_areas,
                start_year=start_ranking_year,
                end_year=end_ranking_year
            )
            
            if not ranked_profs.empty:
                print(ranked_profs.to_string(index=False))
            else:
                print(f"Could not retrieve professor ranking for {top_institution_name}.")
                
        else:
            print("Institution ranking could not be computed or resulted in an empty list.")
    else:
        print("Cannot perform ranking because author publication data failed to load.")


    # --- Original Integrity Check (Optional) ---
    # You can uncomment this if you still want the author check
    # if homepages:
    #     print("\n--- Integrity Check: First 15 Authors Data ---")
    #     authors_to_check = list(homepages.keys())[:15]
    #     for i, author_name in enumerate(authors_to_check):
    #         print(f"\n{i+1}. Author: {author_name}")
    #         print(f"   Homepage: {homepages.get(author_name, 'N/A')}")
    #         print(f"   Scholar ID: {scholar_ids.get(author_name, 'N/A')}")
    #         print(f"   Note: {author_notes.get(author_name, 'N/A')}")
    #         if not homepages.get(author_name):
    #             print("   [WARNING] Homepage missing or empty.")
    # else:
    #     print("\n--- Integrity Check: No author data loaded to check. ---")

