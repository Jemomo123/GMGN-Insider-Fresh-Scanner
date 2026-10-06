import streamlit as st
from fetcher import fetch_gmgn_categorized_wallets

st.set_page_config(
    page_title="GMGN Insider & Fresh Scanner",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ GMGN Insider & Fresh Scanner")
st.caption("Filters out DEX infrastructure, Market Makers, and MEV bots to isolate high-conviction targets.")

st.markdown("---")

col_input, col_btn = st.columns([4, 1])

with col_input:
    token_ca = st.text_input(
        "Token Contract Address (CA):",
        placeholder="Paste Solana token address...",
        label_visibility="collapsed"
    )

with col_btn:
    scan_triggered = st.button("🚀 Extract Wallets", use_container_width=True)

if scan_triggered:
    if not token_ca or len(token_ca.strip()) < 30:
        st.warning("Please enter a valid Solana contract address.")
    else:
        clean_ca = token_ca.strip()
        with st.spinner("Analyzing GMGN holder tags..."):
            results, status = fetch_gmgn_categorized_wallets(clean_ca)
            
            if status == "Success":
                insiders = results.get("insiders", [])
                fresh = results.get("fresh", [])
                
                st.success(f"Found {len(insiders)} Insider Wallets and {len(fresh)} Fresh Wallets.")
                st.markdown("---")
                
                c1, c2 = st.columns(2)
                
                with c1:
                    st.subheader(f"🕵️ Insiders ({len(insiders)})")
                    st.caption("Early-entrant profitable traders.")
                    if insiders:
                        st.code("\n".join(insiders), language="text")
                    else:
                        st.info("No insider wallets flagged by GMGN for this token.")
                
                with c2:
                    st.subheader(f"🌱 Fresh Wallets ({len(fresh)})")
                    st.caption("New accounts (<48h) for tracing funding sources.")
                    if fresh:
                        st.code("\n".join(fresh), language="text")
                    else:
                        st.info("No fresh wallets flagged by GMGN for this token.")
            else:
                st.error(f"Failed to fetch data: {status}")
