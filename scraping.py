import requests
import time
import csv
import os
import sqlite3
from bs4 import BeautifulSoup

# Googleのリポジトリ一覧ページ
base_url = "https://github.com/orgs/google/repositories"

# 保存ファイル
csv_file = "repositories.csv"
checkpoint_file = "checkpoint.txt"
db_file = "repositories.db"

# 前回の続きから開始する
if os.path.exists(checkpoint_file):
    with open(checkpoint_file, "r") as f:
        page = int(f.read().strip())
else:
    page = 1

# CSVファイルが存在するか確認
if not os.path.exists(csv_file) or os.path.getsize(csv_file) == 0:
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Repository", "Language", "Stars"])

print("取得開始ページ:", page)

# HTTPリクエスト用のセッション
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

# ページ取得処理
while True:
    url = f"{base_url}?page={page}"

    print(f"\n--- {page}ページ目を取得中 ---")

    retry_count = 0

    while True:
        # 1ページごとに1秒待機
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

    repo_items = soup.find_all("li", class_="listItem__X41oTe")

    if len(repo_items) == 0:
        print("リポジトリが見つかりません。終了します。")
        break

    page_count = 0

    # CSVに保存
    with open(csv_file, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        for item in repo_items:

            # リポジトリ名を取得
            repo_link = None

            for link in item.find_all("a", href=True):
                href = link["href"]

                if href.startswith("/google/") and href.count("/") == 2:
                    repo_link = link
                    break

            if repo_link is None:
                continue

            repo_name = repo_link["href"].split("/")[-1]

            # 主要な言語を取得
            language_tag = item.select_one(
                'span[class*="PrimaryLanguageName"]'
            )

            language = (
                language_tag.get_text(strip=True)
                if language_tag else "不明"
            )

            # スター数を取得
            star_tag = item.select_one('a[href$="/stargazers"]')

            stars = (
                star_tag.get_text(strip=True)
                if star_tag else "不明"
            )

            writer.writerow([repo_name, language, stars])

            page_count += 1

    # 次のページへ
    page += 1

    # 次回の開始ページを保存
    with open(checkpoint_file, "w") as f:
        f.write(str(page))

    print("このページの取得件数:", page_count)
    print("次回の開始ページ:", page)


# CSVのデータをSQLiteに登録
print("\n--- SQLiteへの保存処理 ---")

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 既存のテーブルを削除
cursor.execute("DROP TABLE IF EXISTS repositories")

# テーブルを新しく作成
cursor.execute("""
    CREATE TABLE repositories (
        repository TEXT PRIMARY KEY,
        language TEXT,
        stars TEXT
    )
""")

# CSVからデータを読み込む
with open(csv_file, "r", newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for row in reader:
        cursor.execute("""
            INSERT OR IGNORE INTO repositories
            (repository, language, stars)
            VALUES (?, ?, ?)
        """, (
            row["Repository"],
            row["Language"],
            row["Stars"]
        ))

# データベースに変更を確定
conn.commit()

print("SQLiteへの保存が完了しました。")

# SELECT文でデータを取得
cursor.execute("""
    SELECT repository, language, stars
    FROM repositories
""")

results = cursor.fetchall()

print("\n--- SQLite保存データ ---")

for row in results:
    print(row)

print("\n登録されているデータ件数:", len(results))

# データベースを閉じる
conn.close()

print("\n--- 処理終了 ---")
print("CSV保存先:", csv_file)
print("SQLite保存先:", db_file)
