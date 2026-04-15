#!/usr/bin/env python3
"""Comprueba que las dependencias del curso importan correctamente (usar con: uv run python scripts/verify_env.py)."""

from __future__ import annotations

import importlib
import sys
from typing import Iterable


def _try(mod: str, label: str | None = None) -> None:
    name = label or mod
    try:
        importlib.import_module(mod)
    except Exception as e:
        print(f"ERROR  {name}: {e}", file=sys.stderr)
        raise
    print(f"OK     {name}")


def main() -> None:
    # Orden: livianos primero; crewai/streamlit al final (más pesados).
    core: Iterable[tuple[str, str | None]] = [
        ("openai", None),
        ("langchain", None),
        ("langchain_core", None),
        ("langchain_openai", None),
        ("langchain_community", None),
        ("langchain_text_splitters", None),
        ("langchain_classic.chains", "langchain_classic.chains (RetrievalQA, etc.)"),
        ("langchain_classic.agents", "langchain_classic.agents"),
        ("langchain_classic.memory", "langchain_classic.memory"),
        ("langgraph", None),
        ("langsmith", None),
        ("faiss", None),
        ("tiktoken", None),
        ("pandas", None),
        ("numpy", None),
        ("sklearn", None),
        ("matplotlib", None),
        ("plotly", None),
        ("seaborn", None),
        ("requests", None),
        ("httpx", None),
        ("dotenv", None),
        ("pydantic", None),
        ("jupyter", None),
        ("ipykernel", None),
        ("pytest", None),
        ("wikipedia", None),
        ("lxml", None),
        ("IPython", None),
    ]
    heavy: Iterable[tuple[str, str | None]] = [
        ("streamlit", None),
        ("crewai", None),
        ("crewai_tools", None),
    ]

    print(f"Python {sys.version.split()[0]} — verificando imports…\n")
    for mod, label in core:
        _try(mod, label)
    for mod, label in heavy:
        _try(mod, label)
    print("\nListo: entorno coherente con pyproject.toml / uv.lock.")


if __name__ == "__main__":
    main()
