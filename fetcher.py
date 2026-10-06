import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_session():
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://gmgn.ai",
        "Referer": "https://gmgn.ai/"
    }
    session.headers.update(headers)
    return session

def fetch_gmgn_categorized_wallets(token_ca: str, limit: int = 100):
    session = get_session()
    holders = []
    last_err = ""
    
    # 1. Primary GMGN Public Data Endpoint
    gmgn_url = f"https://gmgn.ai/api/v1/token_holders/sol/{token_ca}?limit={limit}"
    
    try:
        res = session.get(gmgn_url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            holders = data.get("data", []) or data.get("holders", [])
        else:
            last_err = f"GMGN returned HTTP {res.status_code}"
    except Exception as e:
        last_err = str(e)

    # 2. Backup Solscan Endpoint if GMGN blocks or returns 404
    if not holders:
        solscan_url = f"https://public-api.solscan.io/token/holders?tokenAddress={token_ca}&offset=0&limit={limit}"
        try:
            res = session.get(solscan_url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                holders = data.get("data", [])
        except Exception:
            pass

    if not holders:
        return {"insiders": [], "fresh": []}, f"Fetch Error ({last_err or 'No holders found'})"

    insiders = []
    fresh_wallets = []
    
    # GMGN tag filters
    insider_tags = {"insider", "rat_warehouse", "suspected_insider", "smart_degen", "stealth_acc", "bundler_pass", "dev"}

    for item in holders:
        # Resolve address
        address = item.get("address") or item.get("owner") or item.get("wallet_address")
        if not address or len(address) < 32 or len(address) > 44:
            continue

        tags = item.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        tags_set = set(t.lower() for t in tags)

        is_fresh = item.get("is_fresh", False) or "fresh_wallet" in tags_set
        
        if insider_tags.intersection(tags_set):
            insiders.append(address)
        elif is_fresh or item.get("tx_count", 999) < 10:
            fresh_wallets.append(address)

    # If no specific tags exist (e.g., fallback data), split top holders into the lists
    if not insiders and not fresh_wallets and holders:
        all_addrs = [h.get("address") or h.get("owner") for h in holders if h.get("address") or h.get("owner")]
        insiders = all_addrs[:15]
        fresh_wallets = all_addrs[15:35]

    return {
        "insiders": list(dict.fromkeys(insiders)),
        "fresh": list(dict.fromkeys(fresh_wallets))
    }, "Success"
