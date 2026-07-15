from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Iterable


class UnionFind:
    def __init__(self, items: Iterable[str]) -> None:
        self.parent = {item: item for item in items}
        self.rank = {item: 0 for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1

    def labels(self, prefix: str) -> dict[str, str]:
        root_to_label: dict[str, str] = {}
        labels: dict[str, str] = {}
        for item in self.parent:
            root = self.find(item)
            if root not in root_to_label:
                root_to_label[root] = f"{prefix}_{len(root_to_label):06d}"
            labels[item] = root_to_label[root]
        return labels


def connect_by_bucket(
    request_ids: Iterable[str], buckets: dict[str, set[str]], max_bucket_size: int
) -> UnionFind:
    uf = UnionFind(request_ids)
    for members in buckets.values():
        if 1 < len(members) <= max_bucket_size:
            iterator = iter(members)
            first = next(iterator)
            for member in iterator:
                uf.union(first, member)
    return uf


def inverted_index(features_by_request: dict[str, Iterable[str]]) -> dict[str, set[str]]:
    buckets: dict[str, set[str]] = defaultdict(set)
    for request_id, values in features_by_request.items():
        for value in values:
            buckets[value].add(request_id)
    return buckets


def candidate_pairs(buckets: dict[str, set[str]], max_bucket_size: int) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for members in buckets.values():
        if 1 < len(members) <= max_bucket_size:
            for left, right in combinations(sorted(members), 2):
                pairs.add((left, right))
    return pairs
