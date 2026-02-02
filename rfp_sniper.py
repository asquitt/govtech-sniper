import requests
import json
from datetime import datetime, timedelta

# CONFIGURATION
# ---------------------------------------------------------
# PASTE YOUR API KEY HERE
API_KEY = "SAM-e73293a6-04ad-417e-85f6-de79d559d6c8"
BASE_URL = "https://api.sam.gov/prod/opportunities/v2/search"

def fetch_rfps(keyword, days_back=90):
    """
    Fetches active RFPs from SAM.gov based on a keyword.
    """
    
    # 1. Calculate Date Range (SAM requires specific date format: MM/dd/yyyy)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    params = {
        "api_key": API_KEY,
        "postedFrom": start_date.strftime("%m/%d/%Y"),
        "postedTo": end_date.strftime("%m/%d/%Y"),
        "keywords": keyword,
        "active": "true",        # Only show active bids
        "limit": 10,             # Number of results to fetch
        "ptype": "o,k",          # 'o' = Solicitation, 'k' = Combined Synopsis/Solicitation
        "sort": "-postedDate"    # Newest first
    }

    print(f"[*] Scanning SAM.gov for '{keyword}' opportunities (last {days_back} days)...")
    
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status() # Check for HTTP errors
        data = response.json()
        
        # 2. Parse Results
        if "opportunitiesData" not in data:
            print("[!] No opportunities data found. Check API key or search terms.")
            return

        opportunities = data["opportunitiesData"]
        print(f"[*] Found {len(opportunities)} active opportunities.\n")
        print("-" * 80)

        for opp in opportunities:
            # Extract basic metadata
            title = opp.get("title", "No Title")
            solicitation_id = opp.get("solicitationNumber", "N/A")
            agency = opp.get("organizationHierarchy", [{}])[0].get("name", "Unknown Agency")
            posted_date = opp.get("postedDate", "N/A")
            
            # Extract Links (The "Gold")
            # The API returns a direct link to the opportunity page
            ui_link = opp.get("uiLink", "N/A")
            
            # Sometimes direct resource links (ZIPs/PDFs) are in 'resourceLinks'
            # Note: Direct file download via API often requires higher auth (System Account),
            # but the 'uiLink' is reliable for the user to click.
            resource_links = opp.get("resourceLinks", [])
            download_url = resource_links[0] if resource_links else "No direct file link (Visit UI Link)"

            # 3. Print Clean Output
            print(f"TITLE:    {title}")
            print(f"AGENCY:   {agency}")
            print(f"SOL IC #: {solicitation_id}")
            print(f"POSTED:   {posted_date}")
            print(f"LINK:     {ui_link}")
            print("-" * 80)

    except requests.exceptions.RequestException as e:
        print(f"[!] Error fetching data: {e}")

# --- EXECUTION ---
if __name__ == "__main__":
    # You can change 'Cybersecurity' to any term like 'SaaS', 'Construction', 'Janitorial'
    fetch_rfps("Cybersecurity")
