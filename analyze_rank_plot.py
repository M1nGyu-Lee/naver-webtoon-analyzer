import csv
import matplotlib.pyplot as plt

# 한글 폰트 (Windows 기준)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

CSV_PATH = "webtoons.csv"


def load_ranks():
    items = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                r = int(row.get("rank", "0") or 0)
            except ValueError:
                continue
            items.append({"title": row.get("title", ""), "rank": r})
    return sorted(items, key=lambda x: x["rank"])


def main():
    items = load_ranks()
    if not items:
        print("rank 데이터가 없습니다.")
        return

    print(f"총 작품 수: {len(items)}")

    top10 = items[:10]
    bottom10 = items[-10:]

    print("\n[상위 10개]")
    for w in top10:
        print(f"#{w['rank']:3d}  {w['title']}")

    print("\n[하위 10개]")
    for w in bottom10:
        print(f"#{w['rank']:3d}  {w['title']}")

    # 상위 10개 막대 그래프
    plt.figure(figsize=(8, 4))
    titles_top = [w["title"] for w in top10]
    ranks_top = [w["rank"] for w in top10]
    plt.barh(titles_top, ranks_top)
    plt.gca().invert_yaxis()
    plt.gca().invert_xaxis()
    plt.title("상위 10개 웹툰 (rank 기준)")
    plt.xlabel("rank (작을수록 상위)")
    plt.tight_layout()

    # 하위 10개 막대 그래프
    plt.figure(figsize=(8, 4))
    titles_bot = [w["title"] for w in bottom10]
    ranks_bot = [w["rank"] for w in bottom10]
    plt.barh(titles_bot, ranks_bot)
    plt.gca().invert_yaxis()
    plt.title("하위 10개 웹툰 (rank 기준)")
    plt.xlabel("rank (작을수록 상위)")
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()

