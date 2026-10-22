from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from seonex.crawler import WebsiteCrawler
from seonex.explanations import explain_conflict
from seonex.intent_classifier import INTENTS, classify_intent
from seonex.keyword_similarity import compute_keyword_similarity
from seonex.risk_engine import build_conflicts
from seonex.semantic_similarity import compute_semantic_similarity
from seonex.snapshot_comparison import compare_snapshots
from seonex.storage import (get_intent_overrides, get_labels, get_reviews, list_snapshots,
                            load_snapshot, pair_key, save_intent_override, save_label,
                            save_review, save_snapshot)
from seonex.evaluation import evaluate_binary_conflicts

st.set_page_config(page_title="SEONEX · Explainable SEO Intelligence", page_icon="◈", layout="wide")
st.markdown('''<style>.stApp{background:#1e1e2e;color:#cdd6f4}[data-testid="stSidebar"]{background:#181825}h1,h2,h3{color:#cdd6f4}div[data-testid="stMetric"]{background:#313244;border:1px solid #45475a;border-radius:14px;padding:14px}.stButton>button{background:#89b4fa;color:#11111b;border:0;font-weight:700}.stTabs [data-baseweb="tab"]{color:#bac2de}.stTabs [aria-selected="true"]{color:#cba6f7}</style>''', unsafe_allow_html=True)
DATA_DIR = Path("data/crawls")

def run_scan(url: str, max_pages: int, local_demo: bool):
    status, bar = st.empty(), st.progress(0)
    def progress(done, limit, message): bar.progress(min(done / limit, 1.0), text=message)
    crawler = WebsiteCrawler(url, max_pages=max_pages, allow_local_demo=local_demo, progress_callback=progress)
    result = crawler.crawl(); status.empty(); bar.empty()
    if not result.pages: return result, [], "No crawlable HTML pages were retrieved."
    overrides = get_intent_overrides()
    for page in result.pages:
        intent = classify_intent(page, overrides.get(page["url"]))
        page["intent"], page["intent_evidence"] = intent.label, ", ".join(intent.evidence)
    _, keyword_pairs, _ = compute_keyword_similarity(result.pages)
    semantic_matrix, semantic_error = compute_semantic_similarity(result.pages)
    conflicts = build_conflicts(result.pages, keyword_pairs, semantic_matrix, semantic_error)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pd.DataFrame(result.pages).drop(columns=["text", "internal_links"], errors="ignore").to_csv(DATA_DIR / f"crawl_{stamp}.csv", index=False)
    save_snapshot(url, result.pages, conflicts)
    return result, conflicts, semantic_error

if "scan" not in st.session_state: st.session_state.scan = None
st.sidebar.markdown("# ◈ SEONEX\n*Explainable SEO Intelligence*")
page = st.sidebar.radio("Navigate", ["Overview", "Website Scanner", "Page Inventory", "Conflict Explorer", "Recommendations", "Before vs After", "Model Evaluation"])
st.sidebar.caption("v0.3 · Explainable diagnostic prototype")

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
        mode = "Hybrid diagnostic" if not scan["semantic_error"] else "Intent-aware diagnostic without semantic signal"
        for col, label, value in zip(st.columns(4), ["Pages crawled", "Failed pages", "Eligible pairs", "High similarity pairs"], [len(result.pages), len(result.errors), len(conflicts), high]): col.metric(label, value)
        st.caption(f"Last scan: {scan['time']} · {mode}")
        if conflicts:
            data = pd.DataFrame(conflicts)
            fig = px.scatter(data, x="keyword_similarity", y="semantic_similarity", color="combined_score", hover_data=["page_a", "page_b", "shared_terms"], color_continuous_scale=["#313244", "#89b4fa", "#cba6f7", "#f38ba8"], title="Keyword vs semantic similarity")
            fig.update_xaxes(tickformat=".0%"); fig.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)

elif page == "Page Inventory":
    st.title("Page Inventory"); scan = st.session_state.scan
    if not scan: st.info("Scan a website first.")
    else:
        pages = pd.DataFrame(scan["result"].pages); search = st.text_input("Search URL, title, or heading")
        if search: pages = pages[pages[["url", "title", "h1"]].fillna("").apply(lambda c: c.str.contains(search, case=False)).any(axis=1)]
        pages["metadata_status"] = pages.apply(lambda r: "Complete" if r["title"] and r["meta_description"] and r["h1"] else "Needs review", axis=1)
        st.dataframe(pages[["url", "title", "h1", "intent", "intent_evidence", "word_count", "metadata_status", "status"]], use_container_width=True, hide_index=True)
        st.download_button("Download crawl inventory (CSV)", pages.to_csv(index=False), "seonex-crawl.csv", "text/csv")
        chosen_url = st.selectbox("Correct an intent label", pages["url"].tolist())
        corrected_intent = st.selectbox("Reviewer intent", INTENTS, index=INTENTS.index(pages.loc[pages.url == chosen_url, "intent"].iloc[0]))
        if st.button("Save intent correction"):
            save_intent_override(chosen_url, corrected_intent)
            st.success("Saved. Re-scan to use this correction in pair analysis.")

elif page == "Conflict Explorer":
    st.title("Conflict Explorer"); scan = st.session_state.scan
    if not scan: st.info("Scan a website first.")
    elif not scan["conflicts"]: st.info("This crawl did not have enough text-bearing pages to compare.")
    else:
        conflicts = scan["conflicts"]; frame = pd.DataFrame(conflicts); threshold = st.slider("Minimum diagnostic score", 0.0, 1.0, 0.15, 0.05)
        visible = frame[frame.combined_score >= threshold].copy()
        for field in ["keyword_similarity", "semantic_similarity", "combined_score"]: visible[field] = visible[field].map(lambda v: "Unavailable" if pd.isna(v) else f"{v:.0%}")
        st.dataframe(visible[["page_a", "page_b", "intent_relationship", "keyword_similarity", "semantic_similarity", "combined_score", "action", "shared_terms"]], use_container_width=True, hide_index=True)
        chosen = st.selectbox("Inspect a pair", range(len(conflicts)), format_func=lambda i: f"{conflicts[i]['title_a']}  ↔  {conflicts[i]['title_b']}")
        item = conflicts[chosen]; left, right = st.columns(2)
        left.markdown(f"### Page A\n[{item['title_a'] or item['page_a']}]({item['page_a']})\n\n`{item['page_a']}`")
        right.markdown(f"### Page B\n[{item['title_b'] or item['page_b']}]({item['page_b']})\n\n`{item['page_b']}`")
        score_label = "Combined diagnostic score" if item["semantic_available"] else "Intent-aware score without semantic signal"
        st.metric(score_label, f"{item['combined_score']:.0%}"); st.write(explain_conflict(item)); st.caption(f"Shared important terms: {item['shared_terms'] or 'No strong shared TF-IDF terms'}")

elif page == "Recommendations":
    st.title("Human review")
    scan = st.session_state.scan
    if not scan: st.info("Scan a website first.")
    else:
        conflicts, reviews = scan["conflicts"], get_reviews()
        index = st.selectbox("Page pair", range(len(conflicts)), format_func=lambda i: f"{conflicts[i]['action']} · {conflicts[i]['title_a']} ↔ {conflicts[i]['title_b']}")
        item = conflicts[index]; review = reviews.get(pair_key(item["page_a"], item["page_b"]), {})
        st.subheader(item["action"]); st.write(item["reason"]); st.info(item["human_review"])
        with st.form("review"):
            decision = st.selectbox("Reviewer decision", ["Pending", "Accepted", "Rejected", "Needs review"], index=["Pending", "Accepted", "Rejected", "Needs review"].index(review.get("decision", "Pending")))
            preferred = st.selectbox("Preferred URL (only if relevant)", ["", item["page_a"], item["page_b"]], index=["", item["page_a"], item["page_b"]].index(review.get("preferred_url", "")) if review.get("preferred_url", "") in ["", item["page_a"], item["page_b"]] else 0)
            note = st.text_area("Reviewer note", value=review.get("note", ""))
            implemented = st.checkbox("Change was implemented outside SEONEX", value=bool(review.get("implemented", False)))
            if st.form_submit_button("Save review"):
                save_review(item["page_a"], item["page_b"], decision, note, preferred, implemented)
                st.success("Review saved. SEONEX has not modified any website.")

elif page == "Before vs After":
    st.title("Before vs After")
    snapshots = list_snapshots()
    if len(snapshots) < 2: st.info("Save at least two scans of the same site to compare actual snapshot pairs.")
    else:
        labels = {row["id"]: f"#{row['id']} · {row['created_at']} · {row['base_url']}" for row in snapshots}
        before_id = st.selectbox("Before snapshot", list(labels), format_func=labels.get, index=1)
        after_id = st.selectbox("After snapshot", list(labels), format_func=labels.get, index=0)
        if before_id == after_id: st.warning("Choose two different snapshots.")
        else:
            comparisons = compare_snapshots(load_snapshot(before_id), load_snapshot(after_id))
            if comparisons:
                comparison_frame = pd.DataFrame(comparisons)
                st.caption("A lower SEONEX score means pages became more distinct according to this project model; it does not prove ranking or traffic improvements.")
                st.dataframe(comparison_frame, use_container_width=True, hide_index=True)
                st.plotly_chart(px.bar(comparison_frame, x="direction", title="Comparable pair risk movement", color="direction", color_discrete_map={"Decreased":"#a6e3a1", "Increased":"#f38ba8", "Unchanged":"#bac2de"}), use_container_width=True)
            else: st.info("No matching page pairs were found between these snapshots.")

else:
    st.title("Model Evaluation")
    scan = st.session_state.scan
    if not scan: st.info("Scan a website first, then label page pairs. Metrics use reviewer labels only.")
    else:
        conflicts = scan["conflicts"]; labels = get_labels()
        item_index = st.selectbox("Pair to label", range(len(conflicts)), format_func=lambda i: f"{conflicts[i]['title_a']} ↔ {conflicts[i]['title_b']}")
        item = conflicts[item_index]; current = labels.get(pair_key(item["page_a"], item["page_b"]), "Related but distinct")
        chosen_label = st.radio("Human label", ["Conflict", "Related but distinct", "No conflict"], index=["Conflict", "Related but distinct", "No conflict"].index(current), horizontal=True)
        if st.button("Save human label"):
            save_label(item["page_a"], item["page_b"], chosen_label); st.success("Label saved.")
        metrics = evaluate_binary_conflicts(conflicts, get_labels(), pair_key)
        if metrics:
            st.caption("Binary evaluation maps only the human label ‘Conflict’ to positive; ‘Related but distinct’ remains preserved in storage.")
            for col, label, value in zip(st.columns(4), ["Labeled pairs", "Precision", "Recall", "F1"], [metrics["labeled_pairs"], metrics["precision"], metrics["recall"], metrics["f1"]]): col.metric(label, value if label == "Labeled pairs" else f"{value:.0%}")
        else: st.info("Evaluation pending — label page pairs first.")
