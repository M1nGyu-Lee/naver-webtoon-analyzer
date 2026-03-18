import csv
from collections import Counter
from itertools import combinations

CSV_PATH = "webtoons.csv"


def load_webtoons():
    webtoons = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_tags = row.get("tags", "")
            # tags 구분자: '|'(기본) 또는 ','(호환)
            if "|" in raw_tags:
                parts = raw_tags.split("|")
            else:
                parts = raw_tags.split(",")
            tags = [t.strip() for t in parts if t.strip()]
            if not tags:
                continue
            webtoons.append({"title": row["title"], "tags": tags})
    return webtoons


def analyze_tags(webtoons, top_k: int = 20):
    tag_counter = Counter()
    pair_counter = Counter()

    for w in webtoons:
        tags = sorted(set(w["tags"]))
        tag_counter.update(tags)
        for a, b in combinations(tags, 2):
            pair_counter[(a, b)] += 1

    print(f"웹툰 수: {len(webtoons)}")

    print("\n[태그 Top %d]" % top_k)
    for tag, cnt in tag_counter.most_common(top_k):
        print(f"{tag:20s}  {cnt:4d} 작품")

    print("\n[동시 등장 태그쌍 Top %d]" % top_k)
    for (a, b), cnt in pair_counter.most_common(top_k):
        print(f"{a:15s} + {b:15s}  ->  {cnt:3d} 작품")


if __name__ == "__main__":
    webtoons = load_webtoons()
    analyze_tags(webtoons, top_k=20)

