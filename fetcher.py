import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_gmgn_session():
    """
    Constructs an HTTP session optimized for GMGN Solana endpoints.
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
        "Origin": "https://gmgn.ai",
        "Referer": "https://gmgn.ai/sol/"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    session.headers.update(headers)
    return session

def fetch_gmgn_categorized_wallets(token_ca: str, limit: int = 100):
    """
    Solana-only wallet extractor for Insiders and Fresh Wallets.
    """
    session = get_gmgn_session()
    
    # Primary & Fallback Endpoints for Solana
    endpoints = [
        f"https://gmgn.ai/defi/quotation/v1/tokens/top_holders/sol/{token_ca}?limit={limit}",
        f"https://gmgn.ai/v1/market/token_top_holders?chain=sol&address={token_ca}&limit={limit}"
    ]
    
    holders = []
    status_msg = "Failed to fetch data"
    
    for url in endpoints:
        try:
            res = session.get(url, timeout=12)
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
                    status_msg = "Success"
                    break
            else:
                status_msg = f"HTTP {res.status_code}"
        except Exception as e:
            status_msg = f"Error: {str(e)}"
            
    if not holders:
        return {"insiders": [], "fresh": []}, status_msg
        
    insiders = []
    fresh_wallets = []
    
    # Comprehensive Solana Insider & Rat tags
    insider_tags = {"insider", "rat_warehouse", "suspected_insider", "smart_degen", "stealth_acc", "bundler_pass"}
    
    for item in holders:
        address = item.get("address") or item.get("wallet_address") or item.get("account_address")
        
        # Verify Solana public key length (Base58 string usually 32-44 characters)
        if not address or len(address) < 32 or len(address) > 44:
            continue
            
        tags = item.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        tags_set = set(t.lower() for t in tags)
        
        is_fresh = item.get("is_fresh", False) or "fresh_wallet" in tags_set
        
        # Category Isolation
        if insider_tags.intersection(tags_set):
            insiders.append(address)
        elif is_fresh:
            fresh_wallets.append(address)
            
    # Deduplicate while preserving rank order
    clean_insiders = list(dict.fromkeys(insiders))
    clean_fresh = list(dict.fromkeys(fresh_wallets))
    
    return {
        "insiders": clean_insiders,
        "fresh": clean_fresh
    }, "Success"
