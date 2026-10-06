import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_gmgn_public_session():
    """
    Creates a browser-emulated HTTP session to query GMGN public web endpoints 
    without requiring a paid GMGN API Key.
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
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://gmgn.ai",
        "Referer": "https://gmgn.ai/sol/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }
    session.headers.update(headers)
    return session

def fetch_gmgn_categorized_wallets(token_ca: str, limit: int = 100):
    session = get_gmgn_public_session()
    
    # Target GMGN public web quotation endpoints
    endpoints = [
        f"https://gmgn.ai/defi/quotation/v1/tokens/top_holders/sol/{token_ca}?limit={limit}",
        f"https://gmgn.ai/v1/market/token_top_holders?chain=sol&address={token_ca}&limit={limit}"
    ]
    
    holders = []
    last_err = ""
    
    for url in endpoints:
        try:
            res = session.get(url, timeout=15)
            if res.status_code == 200:
                json_data = res.json()
                if isinstance(json_data, dict):
                    if "data" in json_data:
                        d = json_data["data"]
                        if isinstance(d, list):
                            holders = d
                        elif isinstance(d, dict):
                            holders = d.get("holders", []) or d.get("rank", []) or d.get("list", [])
                    elif "holders" in json_data:
                        holders = json_data["holders"]
                
                if holders:
                    break
            else:
                last_err = f"HTTP {res.status_code}"
        except Exception as e:
            last_err = str(e)
            
    if not holders:
        return {"insiders": [], "fresh": []}, f"Public Fetch Failed ({last_err})"
        
    insiders = []
    fresh_wallets = []
    
    # GMGN classification tags
    insider_tags = {"insider", "rat_warehouse", "suspected_insider", "smart_degen", "stealth_acc", "bundler_pass"}
    
    for item in holders:
        address = item.get("address") or item.get("wallet_address") or item.get("account_address")
        if not address or len(address) < 32 or len(address) > 44:
            continue
            
        tags = item.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        tags_set = set(t.lower() for t in tags)
        
        is_fresh = item.get("is_fresh", False) or "fresh_wallet" in tags_set
        
        # Isolate lists
        if insider_tags.intersection(tags_set):
            insiders.append(address)
        elif is_fresh:
            fresh_wallets.append(address)
            
    clean_insiders = list(dict.fromkeys(insiders))
    clean_fresh = list(dict.fromkeys(fresh_wallets))
    
    return {
        "insiders": clean_insiders,
        "fresh": clean_fresh
    }, "Success"
