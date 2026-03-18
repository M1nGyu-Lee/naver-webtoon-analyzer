import requests
from bs4 import BeautifulSoup

BASE_URL = "https://comic.naver.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


def fetch_webtoons(max_titles: int = 120, recent_n: int = 10):
    """
    네이버 웹툰 비공식 JSON API를 이용해
    요일별 웹툰의 제목, 썸네일, '최근 N화 평균 별점', 태그, 소개, 링크를 수집한다.

    - max_titles: 상위 몇 개 작품까지만 수집할지 (속도/부하 조절용)
    - recent_n: 최근 몇 화까지 평균 별점을 계산할지
    """
    webtoons = []
    rank = 1

    api_url = f"{BASE_URL}/api/webtoon/titlelist/weekday?order=user"

    try:
        res = requests.get(api_url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print("JSON API 호출 실패:", e)
        return []

    title_list_map = data.get("titleListMap", {})
    seen_ids = set()

    for weekday, titles in title_list_map.items():
        if not isinstance(titles, list):
            continue

        for t in titles:
            title_id = t.get("titleId")
            title_name = t.get("titleName")
            if not title_id or not title_name:
                continue

            if title_id in seen_ids:
                continue
            seen_ids.add(title_id)

            webtoon_link = f"{BASE_URL}/webtoon/list?titleId={title_id}"

            thumbnail = (
                t.get("thumbnailUrl")
                or t.get("thumbnail")
                or t.get("representThumbnail")
                or ""
            )

            description = (
                t.get("synopsis")
                or t.get("introduction")
                or t.get("summary")
                or ""
            )

            recent_rating = 0.0
            tags = []

            try:
                detail_res = requests.get(webtoon_link, headers=HEADERS, timeout=10)
                detail_res.raise_for_status()
                detail_soup = BeautifulSoup(detail_res.text, "html.parser")

                # 최근 N화까지의 별점을 가져와 평균 계산
                episode_ratings = []
                # EpisodeListList__meta_info--... 안의 span.text 선택 (회차별 별점)
                meta_infos = detail_soup.select(
                    "div[class^='EpisodeListList__meta_info--'] span.text"
                )
                for span in meta_infos[:recent_n]:
                    txt = span.get_text(strip=True)
                    try:
                        episode_ratings.append(float(txt))
                    except ValueError:
                        continue

                if episode_ratings:
                    recent_rating = sum(episode_ratings) / len(episode_ratings)

                # JSON에 소개가 없으면 상세 페이지 요약으로 보완
                if not description:
                    summary_tag = detail_soup.select_one(
                        "p[class^='EpisodeListInfo__summary--']"
                    )
                    if summary_tag:
                        description = summary_tag.get_text(strip=True)

                # 태그/장르: 여러 개의 <a class="TagGroup__tag--..."> #게임판타지 등
                tag_anchors = detail_soup.select("a[class^='TagGroup__tag--']")
                for a in tag_anchors:
                    label = a.get_text(strip=True)
                    if label.startswith("#"):
                        label = label[1:]
                    if label:
                        tags.append(label)
            except Exception:
                tags = tags or []

            webtoons.append(
                {
                    "title": title_name,
                    "thumbnail": thumbnail,
                    "recent_rating": recent_rating,
                    "rank": rank,
                    "link": webtoon_link,
                    "description": description,
                    "tags": tags,
                }
            )
            rank += 1

            if max_titles and rank > max_titles:
                print(f"상위 {max_titles}개까지만 수집하고 중단합니다.")
                print(f"크롤링된 웹툰 수: {len(webtoons)}")
                return webtoons

    print(f"크롤링된 웹툰 수: {len(webtoons)}")
    return webtoons