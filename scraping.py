
import requests
import time
import csv
import os
from bs4 import BeautifulSoup

# Googleのリポジトリ一覧ページ
base_url = "https://github.com/orgs/google/repositories"

# 保存ファイル
csv_file = "repositories.csv"
checkpoint_file = "checkpoint.txt"

#GitHub側から一時的なアクセス制限を受けることを防ぐ↓
# 1ページごとの待機時間（秒）
WAIT_TIME = 1

# 前回の続きから開始する
if os.path.exists(checkpoint_file):
    with open(checkpoint_file, "r") as f:
        page = int(f.read().strip())
else:
    page = 1

# CSVファイルが存在するか確認
file_exists = os.path.exists(csv_file)

print("取得開始ページ:", page)

# HTTPリクエスト用のセッション
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

while True:

    url = f"{base_url}?page={page}"

    print(f"\n--- {page}ページ目を取得中 ---")

    # アクセス制限に備えて再試行
    retry_count = 0

    while True:

        time.sleep(1)

        response = session.get(url)

        print("ステータスコード:", response.status_code)

        if response.status_code == 200:
            break

        elif response.status_code == 429:

            retry_count += 1

            retry_after = response.headers.get("Retry-After")

            if retry_after and retry_after.isdigit():
                wait = int(retry_after)
            else:
                wait = min(60 * retry_count, 600)

            print(f"アクセス制限中です。{wait}秒待機します。")

            if retry_count >= 5:
                print("再試行回数の上限に達しました。終了します。")
                break

            time.sleep(wait)

        else:
            print("取得に失敗しました。終了します。")
            break

    if response.status_code != 200:
        break

    # HTMLを解析
    soup = BeautifulSoup(response.text, "html.parser")

    repo_items = soup.find_all(
        "li",
        class_="listItem__X41oTe"
    )

    if len(repo_items) == 0:
        print("リポジトリが見つかりません。終了します。")
        break

    page_count = 0

    # CSVに追記
    with open(
        csv_file,
        "a",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(f)

        # 初回だけ見出しを追加
        if not file_exists:
            writer.writerow(["Repository", "Language", "Stars"])
            file_exists = True

        for item in repo_items:

            repo_link = None

            for link in item.find_all("a", href=True):

                href = link["href"]

                if href.startswith("/google/") and href.count("/") == 2:
                    repo_link = link
                    break

            if repo_link is None:
                continue

            repo_name = repo_link["href"].split("/")[-1]

            # 主要な言語
            language_tag = item.select_one(
                'span[class*="PrimaryLanguageName"]'
            )

            if language_tag is not None:
                language = language_tag.get_text(strip=True)
            else:
                language = "不明"

            # スター数
            star_tag = item.select_one(
                'a[href$="/stargazers"]'
            )

            if star_tag is not None:
                stars = star_tag.get_text(strip=True)
            else:
                stars = "不明"

            writer.writerow([
                repo_name,
                language,
                stars
            ])

            page_count += 1

    # 次回の開始ページを保存
    page += 1

    with open(checkpoint_file, "w") as f:
        f.write(str(page))

    print("このページの取得件数:", page_count)
    print("次回の開始ページ:", page)

print("\n--- 処理終了 ---")
print("保存先:", csv_file)
