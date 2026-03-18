from crawler import fetch_webtoons

if __name__ == "__main__":
    data = fetch_webtoons()
    print("크롤링된 개수:", len(data))
    print("앞부분 3개:", data[:3])