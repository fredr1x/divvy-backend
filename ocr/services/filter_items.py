from itertools import combinations

from rapidfuzz.distance import Levenshtein


def _check_similarity(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    if len(a) == 0:
        return 0.0 if len(b) == 0 else 1.0
    edit_dist = Levenshtein.distance(a, b)
    return edit_dist / len(a)


def filter(results: list):

    receipt = results[0]
    if len(results) > 1:
        for r in results[1:]:
            receipt["items"].extend(r["items"])

    to_remove_price_none = []
    for i, item in enumerate(receipt["items"]):
        if item["price"] is None:
            to_remove_price_none.append(i)

    for i in sorted(to_remove_price_none, reverse=True):
        receipt["items"].pop(i)

    to_remove = []
    for it1, it2 in combinations(range(len(receipt["items"])), 2):
        sim = _check_similarity(
            receipt["items"][it1]["item_name"], receipt["items"][it2]["item_name"]
        )
        if sim < 0.2:
            to_remove.append(it1)

    for ind in sorted(to_remove, reverse=True):
        receipt["items"].pop(ind)

    return receipt
