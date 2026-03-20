from github import Github
from github import RateLimitExceededException, GithubException
from langchain_core.documents import Document
from typing import List
import time
import os


def load_all_user_repos(
    username: str,
    token: str,
    file_extensions: List[str] = [".py", ".md", ".txt", ".yaml", ".yml"],
    skip_repos: List[str] = []
) -> List[Document]:
    """
    Load files from ALL public/private repos of a GitHub user.

    Args:
        username        : GitHub username e.g. "hrushikesh2k1"
        token           : GitHub Personal Access Token
        file_extensions : File types to load
        skip_repos      : List of repo names to skip e.g. ["old-repo", "test"]

    Returns:
        List of LangChain Document objects from all repos
    """

    if not token:
        raise ValueError(
            "[ERROR] GitHub token is missing. "
            "Set GITHUB_TOKEN in your .env file."
        )

    g = Github(token)

    try:
        user = g.get_user(username)
        repos = list(user.get_repos())
    except GithubException as e:
        print(f"[ERROR] Failed to fetch repos for user '{username}': {e}")
        raise

    print(f"[INFO] Found {len(repos)} repos for user: {username}")
    print(f"[INFO] File extensions: {file_extensions}")

    if skip_repos:
        print(f"[INFO] Skipping repos: {skip_repos}")

    all_documents = []

    for i, repo in enumerate(repos, start=1):

        if repo.name in skip_repos:
            print(f"[SKIP] ({i}/{len(repos)}) {repo.name}")
            continue

        print(f"\n[INFO] ({i}/{len(repos)}) Loading repo: {repo.full_name}")

        try:
            repo_docs = _load_single_repo(
                repo=repo,
                file_extensions=file_extensions
            )
            all_documents.extend(repo_docs)
            print(f"[INFO] {repo.name} → {len(repo_docs)} files loaded")

        except RateLimitExceededException:
            # GitHub API rate limit hit — wait and retry
            wait_time = 60
            print(f"[WARN] Rate limit hit. Waiting {wait_time}s before retrying...")
            time.sleep(wait_time)
            try:
                repo_docs = _load_single_repo(repo, file_extensions)
                all_documents.extend(repo_docs)
                print(f"[INFO] {repo.name} → {len(repo_docs)} files loaded (after retry)")
            except Exception as e:
                print(f"[ERROR] Skipping {repo.name} after retry: {e}")

        except GithubException as e:
            # Empty repo or access denied — skip silently
            print(f"[WARN] Skipping {repo.name}: {e.data.get('message', str(e))}")

        except Exception as e:
            print(f"[ERROR] Unexpected error for {repo.name}: {e}")

    print(f"\n[INFO] GitHub total: {len(all_documents)} documents from {len(repos)} repos")
    return all_documents


def _load_single_repo(
    repo,
    file_extensions: List[str]
) -> List[Document]:
    """
    Recursively load all matching files from a single GitHub repo.

    Args:
        repo            : PyGithub repo object
        file_extensions : File types to include

    Returns:
        List of LangChain Document objects
    """
    documents = []

    try:
        contents = list(repo.get_contents(""))
    except GithubException as e:
        # Repo is empty or inaccessible
        raise GithubException(e.status, e.data)

    # Recursively walk through all folders
    while contents:
        file_content = contents.pop(0)

        if file_content.type == "dir":
            # Queue up folder contents for processing
            try:
                contents.extend(repo.get_contents(file_content.path))
            except GithubException:
                print(f"[WARN] Could not access folder: {file_content.path}")
            continue

        # Check file extension
        if not any(file_content.path.endswith(ext) for ext in file_extensions):
            continue

        # Skip large files over 1MB
        if file_content.size > 1_000_000:
            print(f"[WARN] Skipping large file ({file_content.size} bytes): {file_content.path}")
            continue

        try:
            text = file_content.decoded_content.decode("utf-8")

            if not text.strip():
                continue  # skip empty files

            documents.append(Document(
                page_content=text,
                metadata={
                    "source": file_content.path,
                    "source_type": "github",
                    "repo": repo.full_name,
                    "url": file_content.html_url,
                    "file_name": file_content.name,
                    "branch": repo.default_branch
                }
            ))
            print(f"[DEBUG] Loaded: {repo.name}/{file_content.path}")

        except UnicodeDecodeError:
            print(f"[WARN] Skipped binary file: {file_content.path}")
        except Exception as e:
            print(f"[WARN] Skipped {file_content.path}: {e}")

    return documents


def load_github_repo(
    repo_name: str,
    token: str,
    file_extensions: List[str] = [".py", ".md", ".txt", ".yaml", ".yml"]
) -> List[Document]:
    """
    Load files from a single GitHub repo by name.
    Kept for backward compatibility with existing code.

    Args:
        repo_name       : Full repo name e.g. "hrushikesh2k1/chatbot"
        token           : GitHub Personal Access Token
        file_extensions : File types to load

    Returns:
        List of LangChain Document objects
    """
    if not token:
        raise ValueError("[ERROR] GitHub token is missing.")

    g = Github(token)

    try:
        repo = g.get_repo(repo_name)
    except GithubException as e:
        print(f"[ERROR] Could not find repo '{repo_name}': {e}")
        raise

    print(f"[INFO] Loading single repo: {repo_name}")
    documents = _load_single_repo(repo, file_extensions)
    print(f"[INFO] Loaded {len(documents)} files from {repo_name}")
    return documents