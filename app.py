from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from seonex.crawler import WebsiteCrawler
from seonex.explanations import explain_conflict
from seonex.keyword_similarity import compute_keyword_similarity
from seonex.risk_engine import build_conflicts
from seonex.semantic_similarity import compute_semantic_similarity

st.set_page_config(page_title="SEONEX · Explainable SEO Intelligence", page_icon="◈", layout="wide")
st.markdown('''<style>.stApp{background:#1e1e2e;color:#cdd6f4}[data-testid="stSidebar"]{background:#181825}h1,h2,h3{color:#cdd6f4}div[data-testid="stMetric"]{background:#313244;border:1px solid #45475a;border-radius:14px;padding:14px}.stButton>button{background:#89b4fa;color:#11111b;border:0;font-weight:700}</style>''', unsafe_allow_html=True)
DATA_DIR = Path("data/crawls")

def run_scan(url: str, max_pages: int, local_demo: bool):
    status, bar = st.empty(), st.progress(0)
    def progress(done, limit, message): bar.progress(min(done / limit, 1.0), text=message)
    crawler = WebsiteCrawler(url, max_pages=max_pages, allow_local_demo=local_demo, progress_callback=progress)
    result = crawler.crawl(); status.empty(); bar.empty()
    if not result.pages: return result, [], "No crawlable HTML pages were retrieved."
    _, keyword_pairs, _ = compute_keyword_similarity(result.pages)
    semantic_matrix, semantic_error = compute_semantic_similarity(result.pages)
    conflicts = build_conflicts(result.pages, keyword_pairs, semantic_matrix, semantic_error)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pd.DataFrame(result.pages).drop(columns=["text", "internal_links"], errors="ignore").to_csv(DATA_DIR / f"crawl_{stamp}.csv", index=False)
    return result, conflicts, semantic_error

if "scan" not in st.session_state: st.session_state.scan = None
st.sidebar.markdown("# ◈ SEONEX\n*Explainable SEO Intelligence*")
page = st.sidebar.radio("Navigate", ["Overview", "Website Scanner", "Page Inventory", "Conflict Explorer"])
st.sidebar.caption("v0.1 · Diagnostic prototype")

if page == "Website Scanner":
    st.title("Website Scanner")
    st.caption("Crawl an authorised website and calculate real page-to-page similarity. SEONEX never changes the target site.")
    use_demo = st.toggle("Use bundled local demo", value=True, help="Start the demo server first, then scan http://localhost:8000.")
    with st.form("scan"):
        url = st.text_input("Website URL", value="http://localhost:8000" if use_demo else "", placeholder="https://your-authorised-site.example")
        max_pages = st.slider("Maximum pages", 2, 50, 12)
        permitted = st.checkbox("I own this website or have permission to crawl it.")
        submitted = st.form_submit_button("Scan website")
    if submitted:
        if not permitted: st.error("Please confirm authorisation before running a scan.")
        else:
            try:
                with st.spinner("Crawling pages and computing explainable similarity…"):
                    result, conflicts, semantic_error = run_scan(url, max_pages, use_demo)
                st.session_state.scan = {"result": result, "conflicts": conflicts, "semantic_error": semantic_error, "time": datetime.now().strftime("%d %b %Y, %H:%M")}
                if semantic_error: st.warning(f"{semantic_error}. Keyword results are available; semantic scores are intentionally not fabricated.")
                st.success(f"Scan complete: {len(result.pages)} page(s) retrieved, {len(result.errors)} failed.")
            except Exception as exc: st.error(f"Scan could not start: {exc}")
    if st.session_state.scan:
        result = st.session_state.scan["result"]
        if result.errors:
            st.subheader("Crawl errors"); st.dataframe(pd.DataFrame(result.errors), use_container_width=True)
        with st.expander("Crawl activity"): st.code("\n".join(result.log))

elif page == "Overview":
    st.title("SEONEX"); st.subheader("Explainable SEO conflict diagnostics")
    st.write("Find page pairs worth reviewing through transparent keyword and semantic similarity. A high score is a **review signal**, not proof of cannibalization or a Google ranking metric.")
    scan = st.session_state.scan
    if not scan: st.info("No scan yet. Open **Website Scanner**, start the bundled demo server, and select Scan website.")
    else:
        result, conflicts = scan["result"], scan["conflicts"]
        high = sum(c["combined_score"] >= .45 for c in conflicts)
        mode = "Hybrid diagnostic" if not scan["semantic_error"] else "Keyword-only diagnostic (semantic model unavailable)"
        for col, label, value in zip(st.columns(4), ["Pages crawled", "Failed pages", "Eligible pairs", "High similarity pairs"], [len(result.pages), len(result.errors), len(conflicts), high]): col.metric(label, value)
        st.caption(f"Last scan: {scan['time']} · {mode}")
        if conflicts:
            data = pd.DataFrame(conflicts)
            fig = px.scatter(data, x="keyword_similarity", y="semantic_similarity", color="combined_score", hover_data=["page_a", "page_b", "shared_terms"], color_continuous_scale="Magma", title="Keyword vs semantic similarity")
            fig.update_xaxes(tickformat=".0%"); fig.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)

elif page == "Page Inventory":
    st.title("Page Inventory"); scan = st.session_state.scan
    if not scan: st.info("Scan a website first.")
    else:
        pages = pd.DataFrame(scan["result"].pages); search = st.text_input("Search URL, title, or heading")
        if search: pages = pages[pages[["url", "title", "h1"]].fillna("").apply(lambda c: c.str.contains(search, case=False)).any(axis=1)]
        pages["metadata_status"] = pages.apply(lambda r: "Complete" if r["title"] and r["meta_description"] and r["h1"] else "Needs review", axis=1)
        st.dataframe(pages[["url", "title", "h1", "word_count", "metadata_status", "status"]], use_container_width=True, hide_index=True)
        st.download_button("Download crawl inventory (CSV)", pages.to_csv(index=False), "seonex-crawl.csv", "text/csv")

else:
    st.title("Conflict Explorer"); scan = st.session_state.scan
    if not scan: st.info("Scan a website first.")
    elif not scan["conflicts"]: st.info("This crawl did not have enough text-bearing pages to compare.")
    else:
        conflicts = scan["conflicts"]; frame = pd.DataFrame(conflicts); threshold = st.slider("Minimum diagnostic score", 0.0, 1.0, 0.15, 0.05)
        visible = frame[frame.combined_score >= threshold].copy()
        for field in ["keyword_similarity", "semantic_similarity", "combined_score"]: visible[field] = visible[field].map(lambda v: "Unavailable" if pd.isna(v) else f"{v:.0%}")
        st.dataframe(visible[["page_a", "page_b", "keyword_similarity", "semantic_similarity", "combined_score", "shared_terms"]], use_container_width=True, hide_index=True)
        chosen = st.selectbox("Inspect a pair", range(len(conflicts)), format_func=lambda i: f"{conflicts[i]['title_a']}  ↔  {conflicts[i]['title_b']}")
        item = conflicts[chosen]; left, right = st.columns(2)
        left.markdown(f"### Page A\n[{item['title_a'] or item['page_a']}]({item['page_a']})\n\n`{item['page_a']}`")
        right.markdown(f"### Page B\n[{item['title_b'] or item['page_b']}]({item['page_b']})\n\n`{item['page_b']}`")
        score_label = "Combined diagnostic score" if item["semantic_available"] else "Keyword-only review signal"
        st.metric(score_label, f"{item['combined_score']:.0%}"); st.write(explain_conflict(item)); st.caption(f"Shared important terms: {item['shared_terms'] or 'No strong shared TF-IDF terms'}")
