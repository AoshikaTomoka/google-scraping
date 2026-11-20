import requests
from bs4 import BeautifulSoup
from bs4.exceptions import ParserRejectedMarkup
import time
import sqlite3
import re

url = "https://github.com/orgs/google/repositories"

page = 1

conn = sqlite3.connect('github_repositories.db')
cursor = conn.cursor()

# テーブルの作成
cursor.execute("""
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    language TEXT,
    stars INTEGER
)
""")

conn.commit()

# スターの数を整数に変換する関数
def convert_stars(star_text):
    star_text = star_text.strip().lower().replace(',', '')

    if star_text.endswith('k'):
        return int(float(star_text[:-1]) * 1000)
    elif star_text.endswith('m'):
        return int(float(star_text[:-1]) * 1000000)
    else:
        return int(float(star_text))

while True:
    # ページ番号をURLに追加
    current_url = f"{url}?type=all&page={page}"

    print(f"{page}ページ目を取得中")

    try:
        # サーバーの負荷を避けるために1秒待機
        time.sleep(1)

        # HTMLを取得
        response = requests.get(current_url, timeout=10)

        # HTTPエラーがあれば例外にする
        response.raise_for_status()

        # HTMLを解析する
        soup = BeautifulSoup(response.content, 'html.parser')

        # リポジトリ名のリンクを取得
        repo_links = soup.find_all(
            'a',
            attrs={'itemprop': 'name codeRepository'}
        )

        # リポジトリがなければ終了
        if not repo_links:
            print("リポジトリが見つからなかったため終了")
            break

        # 各リポジトリの情報を取得
        for repo_link in repo_links:

            # リポジトリ名を取得
            repo_name = repo_link.get_text(strip=True)

            # リポジトリ情報が入っている親要素
            repo_box = repo_link.find_parent(
                'div',
                class_='Box-row'
            )

            if repo_box is None:
                continue

            # 主要な言語を取得
            language_tag = repo_box.find(
                'span',
                attrs={'itemprop': 'programmingLanguage'}
            )

            if language_tag is not None:
                language = language_tag.get_text(strip=True)
            else:
                language = "不明"

            # スター数を取得
            star_tag = repo_box.find(
                'a',
                href=re.compile(r'/stargazers/?$')
            )

            if star_tag is not None:
                star_text = star_tag.get_text(strip=True)

                try:
                    stars = convert_stars(star_text)
                except ValueError:
                    stars = 0
            else:
                stars = 0

            # データベースに保存
            cursor.execute("""
                INSERT INTO repositories (name, language, stars)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    language = excluded.language,
                    stars = excluded.stars
            """, (repo_name, language, stars))

            print(repo_name, language, stars)

        # データベースに反映
        conn.commit()

    except requests.exceptions.RequestException as e:
        print('アクセスできなかった:', current_url)
        print(e)
        break

    except ParserRejectedMarkup as e:
        print('HTMLを解析できなかった:', current_url)
        print(e)
        break

    # 次のページへ
    page += 1
    # 1ページ目だけ取得して終了
    if page > 1:
        break


# 保存したデータをSELECT文で表示
print("\n===== データベースの内容 =====")

cursor.execute("""
    SELECT name, language, stars
    FROM repositories
    ORDER BY stars DESC
""")

results = cursor.fetchall()

for row in results:
    print(
        'リポジトリ名:', row[0],
        '主要な言語:', row[1],
        'スター数:', row[2]
    )

print('取得したリポジトリ数:', len(results))

# データベースを閉じる
conn.close()

print("スクレイピングとデータベースへの保存が完了")