import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_gmgn_session():
    """
    Constructs a request session with retry logic and standard user headers.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    api_key = os.getenv("GMGN_API_KEY", "")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://gmgn.ai/"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    session.headers.update(headers)
    return session

def fetch_gmgn_categorized_wallets(token_ca: str, chain: str = "sol", limit: int = 100):
    """
    Fetches top token holders/traders directly from GMGN and extracts
    Insiders and Fresh Wallets into clean, isolated address lists.
    """
    session = get_gmgn_session()
    
    url = f"https://gmgn.ai/defi/quotation/v1/tokens/top_holders/{chain}/{token_ca}"
    params = {"limit": limit}
    
    try:
        response = session.get(url, params=params, timeout=15)
        
        # Fallback endpoint if primary v1 quote returns non-200
        if response.status_code != 200:
            alt_url = f"https://gmgn.ai/v1/market/token_top_holders?chain={chain}&address={token_ca}&limit={limit}"
            response = session.get(alt_url, timeout=15)
            
        if response.status_code != 200:
            return None, f"HTTP Error {response.status_code}: Unable to reach GMGN endpoint."
            
        json_data = response.json()
        
        # Parse nested GMGN list structures
        holders = []
        if isinstance(json_data, dict):
            if "data" in json_data:
                d = json_data["data"]
                if isinstance(d, list):
                    holders = d
                elif isinstance(d, dict):
                    holders = d.get("holders", []) or d.get("rank", []) or d.get("list", [])
            elif "holders" in json_data:
                holders = json_data["holders"]
            elif "list" in json_data:
                holders = json_data["list"]
                
        if not holders:
            return {"insiders": [], "fresh": []}, "Success (No holders returned)"
            
        insiders = []
        fresh_wallets = []
        
        # Explicit GMGN Insider & Rat tags
        insider_tags = {"insider", "rat_warehouse", "suspected_insider", "smart_degen"}
        
        for item in holders:
            address = item.get("address") or item.get("wallet_address") or item.get("account_address")
            if not address or len(address) < 32:
                continue
                
            tags = item.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            tags_set = set(t.lower() for t in tags)
            
            is_fresh = item.get("is_fresh", False) or "fresh_wallet" in tags_set
            
            # Categorize into Insiders vs Fresh
            if insider_tags.intersection(tags_set):
                insiders.append(address)
            elif is_fresh:
                fresh_wallets.append(address)
                
        # Deduplicate while preserving order
        clean_insiders = list(dict.fromkeys(insiders))
        clean_fresh = list(dict.fromkeys(fresh_wallets))
        
        return {
            "insiders": clean_insiders,
            "fresh": clean_fresh
        }, "Success"
        
    except Exception as e:
        return None, f"Network Connection Error: {str(e)}"
