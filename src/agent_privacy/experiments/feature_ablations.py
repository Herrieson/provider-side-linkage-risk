from __future__ import annotations

from agent_privacy.features.extract import FeatureOptions

FAST_TEXT_FEATURE_WINDOW_CHARS = 80_000
FAST_MAX_SHINGLES = 8_000
FAST_MAX_WORDS = 5_000


FEATURE_ABLATIONS = {
    "none",
    "no_paths",
    "no_usernames",
    "no_domains",
    "no_traces",
    "no_repo_ids",
    "no_identifiers",
    "no_shingles",
    "no_tool_schema",
    "no_system_prompt",
    "no_tool_system",
    "no_time",
    "no_length",
    "no_time_length",
    "no_cache",
    "no_semantic",
}


def feature_options_for_ablation(
    *,
    methods: list[str],
    fast_features: bool,
    feature_ablation: str,
) -> FeatureOptions:
    if feature_ablation not in FEATURE_ABLATIONS:
        known = ", ".join(sorted(FEATURE_ABLATIONS))
        raise ValueError(f"unknown feature ablation: {feature_ablation}. Known: {known}")
    include_shingles = _methods_need_shingles(methods)
    include_domains = not fast_features
    include_traces = not fast_features
    include_paths = True
    include_usernames = True
    include_repo_ids = True
    include_identifiers = True
    include_tool_fingerprint = True
    include_system_fingerprint = True
    include_time = True
    include_length = True
    include_cache = True
    include_semantic_signatures = _methods_need_semantic(methods)
    text_feature_window_chars = None
    max_shingles = None
    max_words = None
    hash_shingles = False
    scan_full_text = True

    if fast_features:
        text_feature_window_chars = FAST_TEXT_FEATURE_WINDOW_CHARS
        max_shingles = FAST_MAX_SHINGLES
        max_words = FAST_MAX_WORDS
        hash_shingles = True

    if feature_ablation == "no_paths":
        include_paths = False
        include_usernames = False
        include_repo_ids = False
    elif feature_ablation == "no_usernames":
        include_usernames = False
    elif feature_ablation == "no_domains":
        include_domains = False
    elif feature_ablation == "no_traces":
        include_traces = False
    elif feature_ablation == "no_repo_ids":
        include_repo_ids = False
    elif feature_ablation == "no_identifiers":
        include_identifiers = False
        include_paths = False
        include_usernames = False
        include_domains = False
        include_traces = False
        include_repo_ids = False
    elif feature_ablation == "no_shingles":
        include_shingles = False
    elif feature_ablation == "no_tool_schema":
        include_tool_fingerprint = False
    elif feature_ablation == "no_system_prompt":
        include_system_fingerprint = False
    elif feature_ablation == "no_tool_system":
        include_tool_fingerprint = False
        include_system_fingerprint = False
    elif feature_ablation == "no_time":
        include_time = False
    elif feature_ablation == "no_length":
        include_length = False
    elif feature_ablation == "no_time_length":
        include_time = False
        include_length = False
    elif feature_ablation == "no_cache":
        include_cache = False
    elif feature_ablation == "no_semantic":
        include_semantic_signatures = False

    return FeatureOptions(
        include_shingles=include_shingles,
        include_domains=include_domains,
        include_traces=include_traces,
        include_paths=include_paths,
        include_usernames=include_usernames,
        include_repo_ids=include_repo_ids,
        include_identifiers=include_identifiers,
        include_tool_fingerprint=include_tool_fingerprint,
        include_system_fingerprint=include_system_fingerprint,
        include_time=include_time,
        include_length=include_length,
        include_cache=include_cache,
        include_semantic_signatures=include_semantic_signatures,
        **(
            {
                "text_feature_window_chars": text_feature_window_chars,
                "max_shingles": max_shingles,
                "max_words": max_words,
                "hash_shingles": hash_shingles,
                "scan_full_text": scan_full_text,
            }
            if fast_features
            else {}
        ),
    )


def _methods_need_shingles(methods: list[str]) -> bool:
    return any(
        method in {"prefix", "context_only", "hybrid", "provider_lowcost"}
        for method in methods
    )


def _methods_need_semantic(methods: list[str]) -> bool:
    return any(method in {"provider_lowcost"} for method in methods)
