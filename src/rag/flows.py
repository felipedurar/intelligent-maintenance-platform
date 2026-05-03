from __future__ import annotations

import argparse

from prefect import flow, get_run_logger, task

from rag.config import DEFAULT_RAG_PATHS
from rag.indexer import RagIndexer


@task
def index_documentation_task(paths: list[str], base_dir: str) -> dict[str, object]:
    return RagIndexer().index_paths(paths=paths, base_dir=base_dir)


@flow(name="index-rag-documentation")
def index_rag_documentation(
    paths: list[str] | None = None,
    base_dir: str = ".",
) -> dict[str, object]:
    logger = get_run_logger()
    resolved_paths = paths or DEFAULT_RAG_PATHS
    logger.info("Indexing RAG documentation paths: %s", resolved_paths)
    result = index_documentation_task(resolved_paths, base_dir)
    logger.info("RAG indexing finished: %s", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Index documentation into the RAG vector store.")
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--path", action="append", dest="paths")
    args = parser.parse_args()
    index_rag_documentation(paths=args.paths, base_dir=args.base_dir)


if __name__ == "__main__":
    main()
