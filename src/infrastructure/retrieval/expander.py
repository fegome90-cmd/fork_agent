"""Controlled lexical expansion for retrieval queries."""

from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.retrieval.normalizer import NormalizedQuery
from src.infrastructure.retrieval.sanitizer import sanitize_fts5

ALIAS_GROUPS = [
    {"raw", "memory", "archivo", "bruto"},
    {"oficial", "docs", "guia", "guide", "official"},
    {"create", "update", "supersede", "lifecycle", "replace", "updated"},
    {"fallback", "silencioso", "silent", "failure", "contrato", "explicit", "contracts"},
    {"backend", "memoria", "sqlite", "fts5", "retrieval", "stack", "configured"},
    {"kick", "off", "iniciar", "start", "launch", "cli"},
    {"faster", "rapido", "performance", "quick"},
    {"hyphens", "guiones", "dashes", "underscore", "underscores", "paths"},
]

PHRASE_ALIASES = {
    "kick off": ["start", "launch", "iniciar"],
    "official guidance": ["docs", "guide", "oficial"],
    "silent failures": ["silent failure", "fallback contracts"],
    "backend memoria": ["sqlite fts5", "retrieval stack"],
    "gemini faster": ["gemini performance", "gemini rapido"],
    "hyphen underscore": ["hyphens underscores workaround"],
}


@dataclass(frozen=True)
class ExpandedQuery:
    original: str
    normalized: str
    expanded_terms: tuple[str, ...]
    variants: tuple[str, ...]


def alias_variants_for_token(token: str) -> list[str]:
    for group in ALIAS_GROUPS:
        if token in group:
            return sorted(term for term in group if term != token)
    return []


def build_expanded_queries(tokens: list[str]) -> list[str]:
    variants: list[str] = []
    base = " ".join(tokens).strip()
    if base:
        variants.append(base)

    for index, token in enumerate(tokens):
        aliases = alias_variants_for_token(token)
        if not aliases:
            continue
        replacement = tokens[:index] + [aliases[0]] + tokens[index + 1 :]
        variant = " ".join(replacement).strip()
        if variant and variant not in variants:
            variants.append(variant)

    token_phrase = " ".join(tokens)
    for phrase, aliases in PHRASE_ALIASES.items():
        if phrase in token_phrase:
            for alias in aliases:
                variant = sanitize_fts5(alias)
                if variant and variant not in variants:
                    variants.append(variant)

    return variants


def expand_aliases(normalized: NormalizedQuery) -> ExpandedQuery:
    expanded_terms: list[str] = []
    for token in normalized.keywords:
        if token not in expanded_terms:
            expanded_terms.append(token)
        for alias in alias_variants_for_token(token):
            if alias not in expanded_terms:
                expanded_terms.append(alias)

    phrase_key = " ".join(normalized.keywords)
    for phrase, aliases in PHRASE_ALIASES.items():
        if phrase in phrase_key:
            for alias in aliases:
                sanitized = sanitize_fts5(alias)
                if sanitized and sanitized not in expanded_terms:
                    expanded_terms.append(sanitized)

    return ExpandedQuery(
        original=normalized.original,
        normalized=normalized.simplified,
        expanded_terms=tuple(expanded_terms),
        variants=tuple(build_expanded_queries(list(normalized.keywords))),
    )
