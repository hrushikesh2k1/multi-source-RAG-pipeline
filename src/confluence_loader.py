from langchain_community.document_loaders import ConfluenceLoader
from langchain_core.documents import Document
from atlassian import Confluence
from typing import List


def load_all_confluence_spaces(
    url: str,
    username: str,
    api_key: str,
    file_extensions: List[str] = []
) -> List[Document]:
    """
    Load all pages from ALL spaces in Confluence.
    Just like load_all_user_repos() loads all GitHub repos.

    Args:
        url      : Confluence base URL e.g. "https://hrushikeshboora.atlassian.net/wiki"
        username : Atlassian account email
        api_key  : Atlassian API token
    """

    # Step 1: Get all space keys from Confluence
    confluence = Confluence(url=url, username=username, password=api_key)
    spaces = confluence.get_all_spaces(start=0, limit=50)
    space_keys = [space["key"] for space in spaces["results"]]

    print(f"[INFO] Found {len(space_keys)} Confluence spaces: {space_keys}")

    all_documents = []

    # Step 2: Load pages from each space
    for space_key in space_keys:
        print(f"[INFO] Loading Confluence space: {space_key}")
        try:
            loader = ConfluenceLoader(
                url=url,
                username=username,
                api_key=api_key,
                space_key=space_key,
                include_attachments=False,
                limit=50
            )
            docs = loader.load()

            for doc in docs:
                doc.metadata["source_type"] = "confluence"
                doc.metadata["space_key"] = space_key
                print(f"[DEBUG] Loaded page: {doc.metadata.get('title', 'Untitled')} | space: {space_key}")

            all_documents.extend(docs)
            print(f"[INFO] Space '{space_key}' → {len(docs)} pages loaded")

        except Exception as e:
            print(f"[ERROR] Failed to load space '{space_key}': {e}")

    print(f"[INFO] Confluence total: {len(all_documents)} pages from {len(space_keys)} spaces")
    return all_documents