import json
import csv
from datetime import datetime, timezone

from crawler import fetch_webtoons

SOURCE_API = "https://comic.naver.com/api/webtoon/titlelist/weekday?order=user"
ORDER = "user"


def main():
    """
    크롤링 전용 스크립트.
    네이버 웹툰 데이터를 한 번 크롤링해서 webtoons.json / webtoons.csv 파일로 저장한다.

    - 실행 위치: d:\\cursor_project\\webtoon_analyzer
    - 실행 방법: python export_webtoons.py
    """
    # 수집 파라미터 (분석/포트폴리오에서 재현 가능하게 기록)
    max_titles = 120
    recent_n = 10

    data = fetch_webtoons(max_titles=max_titles, recent_n=recent_n)
    print(f"총 크롤링된 웹툰 수: {len(data)}")

    fetched_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    # JSON 저장 (원본, 리스트)
    json_path = "webtoons.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"데이터를 {json_path} 파일로 저장했습니다.")

    # CSV 저장 (분석용, wide)
    csv_path = "webtoons.csv"
    fieldnames = [
        "fetched_at",
        "source_api",
        "order",
        "max_titles",
        "recent_n",
        "rank",
        "title",
        "link",
        "thumbnail",
        "recent_rating",
        "description",
        "tags",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            out = row.copy()
            # 메타 컬럼
            out["fetched_at"] = fetched_at
            out["source_api"] = SOURCE_API
            out["order"] = ORDER
            out["max_titles"] = max_titles
            out["recent_n"] = recent_n

            # description: 줄바꿈 제거(엑셀/CSV 깨짐 방지) + 양끝 공백 정리
            desc = (out.get("description") or "").replace("\r", " ").replace("\n", " ").strip()
            out["description"] = " ".join(desc.split())

            # tags: 리스트 → '|'로 join (쉼표는 CSV와 충돌/가독성 이슈가 있어서 구분자 변경)
            tags = out.get("tags") or []
            out["tags"] = "|".join([t.strip() for t in tags if t and t.strip()])
            writer.writerow({k: out.get(k, "") for k in fieldnames})
    print(f"데이터를 {csv_path} 파일로 저장했습니다.")

    # 사람이 보기 좋은 CSV (엑셀/노션 업로드용)
    pretty_csv_path = "웹툰_제출용.csv"
    # 제출/공유용 컬럼 (별점은 현재 수집 제약이 있어 placeholder로 남김)
    pretty_fields = ["순위", "제목", "최근화_별점", "평균_별점", "링크"]
    with open(pretty_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        # utf-8-sig: 엑셀에서 한글 깨짐 방지
        writer = csv.DictWriter(f, fieldnames=pretty_fields)
        writer.writeheader()
        for row in data:
            writer.writerow(
                {
                    "순위": row.get("rank", ""),
                    "제목": row.get("title", ""),
                    "최근화_별점": "-",
                    "평균_별점": "-",
                    "링크": row.get("link", ""),
                }
            )
    print(f"데이터를 {pretty_csv_path} 파일로 저장했습니다.")


if __name__ == "__main__":
    main()

