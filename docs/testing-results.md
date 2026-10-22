# Testing results

**22 October 2026**

| Check | Result | Evidence |
|---|---|---|
| Unit tests | Pass | `9 passed` via `.venv\Scripts\python.exe -m pytest -q` |
| Local demo crawl | Pass in prior v0.1 validation | 10 retrieved pages, 0 crawl errors, 45 TF-IDF candidate pairs |
| Semantic failure path | Pass in prior v0.1 validation | clear `Semantic model unavailable` result with no fabricated semantic values |
| Full semantic model download/inference | Pending | requires first model download/runtime verification |
| Streamlit startup | Pass | `http://localhost:8512/_stcore/health` returned `ok` |

Test results describe local development only. They do not prove a public deployment or search-engine indexing.
