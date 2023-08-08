import requests
from bs4 import BeautifulSoup
import pymysql
from pprint import pprint

def scrape_data(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # ... (スクレイピングとデータの解析処理)
    print("Scraped data ===================")
    pprint(soup)
    
    pageTitle = soup.select("title")
 
    pageTitle[0] = pageTitle[0].text
    print("Page title =", pageTitle[0])

    pageInfo = {'title': pageTitle[0]}
    return pageInfo



    # 編集が追いつかない？ nanigotoda 2019/12/01

    # if not soup.find('div', class_='st-pg_contents') :
    #     print_red('Nothing any response in this article.', is_bold=True)
    #     return None

    # # レス数が30件以下の場合、navi自体が存在しないため、除外操作の前に実在チェック
    # if soup.find('a', class_='navi') :
    #     # 記事タイトルが半角数値を含むとNaviタグの項目を拾ってしまうため除外
    #     soup.find('a', class_='navi').decompose()

    # # ページャー部分を取得。
    # pagers = soup.select("div.st-pg_contents")


def get_DB_connection():
    conn = pymysql.connect(
        host='db_container',  # docker-compose.ymlで設定したサービス名
        user='myuser',
        password='mypassword',
        db='mydatabase',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    return conn

def save_data_to_db(data):
    conn = pymysql.connect(
        host='db_container',  # docker-compose.ymlで設定したサービス名
        user='myuser',
        password='mypassword',
        db='mydatabase',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    # ... (データをDBに保存する処理)



    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO `titles` (`title`) VALUES (%s)"
            cursor.execute(sql, (data['title']))
            conn.commit()

            sql = "INSERT INTO `titles` (`title`) VALUES (%s)"
            cursor.execute(sql, ("message"))
            conn.commit()

            qry = "SELECT * FROM `titles`"
            cursor.execute(qry)
            results = cursor.fetchall()
            for row in results:
                print(row)
            
            qry = "DELETE from `titles`"
            cursor.execute(qry)
            conn.commit()

            qry = "ALTER TABLE  `titles` AUTO_INCREMENT = 1"
            cursor.execute(qry)
            conn.commit()
    finally:
        conn.close()

    print("data[title] =", data['title'])

    conn = pymysql.connect(
        host='db_container',  # docker-compose.ymlで設定したサービス名
        user='myuser',
        password='mypassword',
        db='mydatabase',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with conn.cursor() as cursor:

            insert_resAry = []

            insert_dic = { "article_id": "1010", "title": "SampleTitle a", "url": "http://example.com", "moved": False, "new_id": None }
            insert_resAry.append(insert_dic)

            insert_dic = { "article_id": "1020", "title": "SampleTitle b", "url": "http://example.com", "moved": False, "new_id": None }
            insert_resAry.append(insert_dic)

            insert_dic = { "article_id": "1030", "title": "SampleTitle c", "url" : "http://example.com", "moved": False, "new_id": None }
            insert_resAry.append(insert_dic)

            qry = """INSERT INTO article_list (article_id, title, url, moved, new_id) VALUES (%(article_id)s, %(title)s, %(url)s, %(moved)s, %(new_id)s)"""

            for insert_data in insert_resAry:
                cursor.execute(qry, insert_data)

            # cursor.execute(qry, insert_dic)

            conn.commit()

            qry = "SELECT * FROM `article_list`"
            cursor.execute(qry)
            results = cursor.fetchall()
            print("Check table of article_list ===================")
            for row in results:
                print(row)
            
            qry = "DELETE from `article_list`"
            cursor.execute(qry)
            conn.commit()

            qry = "ALTER TABLE  `article_list` AUTO_INCREMENT = 1"
            cursor.execute(qry)
            conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    data = scrape_data("http://example.com")
    print("data = ", data)
    print(type(data))
    save_data_to_db(data)
