import csv
from collections import Counter

CSV_PATH = "webtoons.csv"


def load_webtoons():
    items = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rank = int(row.get("rank", "0") or 0)
            except ValueError:
                rank = 0
            items.append(
                {
                    "title": row.get("title", ""),
                    "rank": rank,
                    "recent_rating": float(row.get("recent_rating", "0") or 0.0),
                    "link": row.get("link", ""),
                }
            )
    return items


def analyze_rank_distribution(items):
    print(f"총 작품 수: {len(items)}")
    if not items:
        return

    # 상위/중위/하위 구간 나누기 (rank 기준)
    items = sorted(items, key=lambda x: x["rank"])
    top_n = min(20, len(items))

    print("\n[상위 %d개 작품]" % top_n)
    for w in items[:top_n]:
        print(f"#{w['rank']:3d}  {w['title']}")

    print("\n[하위 %d개 작품]" % top_n)
    for w in items[-top_n:]:
        print(f"#{w['rank']:3d}  {w['title']}")


def analyze_rating_basic(items):
    ratings = [w["recent_rating"] for w in items if w["recent_rating"] > 0]
    if not ratings:
        print("\n[최근평점 분석]\n수집된 최근평점 정보가 없습니다.")
        return

    avg = sum(ratings) / len(ratings)
    print("\n[최근평점 분석]")
    print(f"평점이 있는 작품 수: {len(ratings)}")
    print(f"평균 최근평점: {avg:.2f}")


if __name__ == "__main__":
    webtoons = load_webtoons()
    analyze_rank_distribution(webtoons)
    analyze_rating_basic(webtoons)

