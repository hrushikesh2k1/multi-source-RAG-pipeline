from src.vectorstore import FaissVectorStore
from src.search import RAGSearch
from src.github_loader import load_all_user_repos
from src.confluence_loader import load_all_confluence_spaces
import argparse
import time
import os

FAISS_DIR = "faiss_store"
faiss_index_path = os.path.join(FAISS_DIR, "faiss.index")

def is_index_stale(max_age_hours=24):
    if not os.path.exists(faiss_index_path):
        return True
    age_hours = (time.time() - os.path.getmtime(faiss_index_path)) / 3600
    print(f"[INFO] FAISS index age: {age_hours:.1f} hours")
    return age_hours > max_age_hours

def build_index():
    all_docs = []

    token = "your_github_token_here"       # ← never hardcode, use .env
    github_docs = load_all_user_repos(
        username="hrushikesh2k1",
        token=token,
        file_extensions=[".md", ".txt", ".py"]
    )
    all_docs.extend(github_docs)

    confluence_docs = load_all_confluence_spaces(
        url="https://hrushikeshboora.atlassian.net/wiki",
        username="hrushikeshboora@gmail.com",         # ← never hardcode, use .env
        api_key="your_api_key_here"        # ← never hardcode, use .env
    )
    all_docs.extend(confluence_docs)

    print(f"[INFO] Total documents from all sources: {len(all_docs)}")

    store = FaissVectorStore(FAISS_DIR)
    store.build_from_documents(all_docs)
    return store

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--max-age", type=int, default=24)
    args = parser.parse_args()

    if args.rebuild or is_index_stale(max_age_hours=args.max_age):
        store = build_index()
    else:
        print("[INFO] Index is fresh — loading existing index.")
        store = FaissVectorStore(FAISS_DIR)
        store.load()

    rag_search = RAGSearch()
    query = "How is authentication implemented in the chatbot?"
    summary = rag_search.search_and_summarize(query, top_k=50)
    print("Summary:", summary)