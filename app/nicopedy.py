import sys
import os

import requests
from requests.packages.urllib3.util import ssl_

import urllib.request
import ssl

from bs4 import BeautifulSoup
import re # 正規表現用
from time import sleep      # 待ち時間用
from sqlalchemy import and_, or_, not_

# Local
# Set import module directory
current_dir = os.path.dirname(os.path.abspath(__file__))
import_dir = os.path.join(current_dir, 'util')
sys.path.append(import_dir)

from debug_tools import debug_print
from db_operator import Database
from models import Website, Config, ArticleList, ArticleDetail
from error_handler import ErrorHandler, PROGRAM_EXIT, PROGRAM_CONTINUE

class NicopediScraper:
    def __init__(self, db):
        self.db = db

    # 対象が適正なニコ記事かどうかチェック.
    def is_valid_url(self, targetArtURL):

        # ニコニコ記事のURLかどうかチェック ----------------------------#
        # DBからニコニコ記事のURLを取得
        filter_condition = and_(Website.name == "Niconico")
        # print("fileter condition =", filter_condition)
        websites = self.db.select(Website, filter_condition)
        # print("websites =", websites)
        nico_url = websites[0].url
        # print("nico_url =", nico_url)
        is_Nicopedi_URL = targetArtURL.startswith(nico_url)
        # ---------------------------------------------------------#

        return is_Nicopedi_URL
    
    def scrape_article_top(self, url):
        ####################################################
        # http://yamori-jp.blogspot.com/2022/09/python-ssl-unsafelegacyrenegotiationdis.html
        ctx = ssl.create_default_context()
        ctx.options |= 0x4
        # 対象記事が存在しない場合のハンドリング
        try:
            with urllib.request.urlopen(url, context=ctx) as response:
                web_content = response.read()
            soup = BeautifulSoup(web_content, "html.parser")
        except urllib.error.HTTPError as e:
            ErrorHandler.handle_error(e, f"HTTP error occurred: {e.code}", PROGRAM_EXIT)
            return None
        except urllib.error.URLError as e:
            ErrorHandler.handle_error(e, f"URL error occurred: {e.reason}", PROGRAM_EXIT)
            return None
        ####################################################
        return soup

    def is_article_exist(self, soup):
        # # 記事内容が存在するページかチェック ----------------------------#
        # # 「存在しない記事」にのみ存在するクラスを取得
        # filter_condition = and_(Config.config_type == "ARTICLE NOT EXIST CLASS")
        # configs = self.db.select(Config, filter_condition)
        # config_value = configs[0].value
        # print("config_value =", config_value)
        # # ---------------------------------------------------------#

        # class_exists = soup.find(class_=config_value) != None

        debug_print("Func: is_article_exist()")
        return self.is_exist_target_class(soup, "ARTICLE NOT EXIST CLASS")

    def is_bbs_exist(self, soup):
        debug_print("Func: is_bbs_exist()")
        return self.is_exist_target_class(soup, "RES NOT EXIST CLASS")

    def is_exist_target_class(self, soup, tag):
        debug_print("Func: is_exist_target_class(), tag = ", tag)
        filter_condition = and_(Config.config_type == tag)
        configs = self.db.select(Config, filter_condition)
        config_value = configs[0].value

        debug_print("config_value =", config_value)

        class_exists = soup.find(class_=config_value) != None

        debug_print("Exist check = ", class_exists)

        return class_exists

    # 記事タイトルを取得
    def get_title(self, soup):
        # Titleが含まれるクラスを取得
        article_title = soup.find("div", class_="a-title")

        # 不要な情報の除去
        if article_title.find('span', class_='st-label_title-category') != None :
            article_title.find('span', class_='st-label_title-category').decompose()
        if article_title.find('div', class_='a-title-yomi') != None :
            article_title.find('div', class_='a-title-yomi').decompose()
        if article_title.find('div', class_='a-title-article-text-count-wrap') != None :
            article_title.find('div', class_='a-title-article-text-count-wrap').decompose()
        if article_title.find('ul', class_='article-title-counter') != None :
            article_title.find('ul', class_='article-title-counter').decompose()

        # 残ったテキストから前後の空白と開業をトリム。後処理の簡便化のためスペースをアンダーバーに置換。
        article_title = article_title.getText()
        article_title = article_title.strip()
        article_title = article_title.strip('\n')
        article_title = article_title.replace(' ', '_')

        return article_title
    
    # BBSの最終ページ番号を取得
    def get_bbs_length(self, soup):
        
        # st-pg_contentsクラスが存在しない場合は掲示板レス自体が存在しない
        if not soup.find("div", class_="st-pg_contents"):
            debug_print("No div class = st-pg_contents")
            return None
        
        # st-pg_contents下にあるaタグを取得
        pagers = soup.select("div.st-pg_contents > a")
        # debug_print("pagers = ", pagers)

        # 取得した要素が一つだけだった場合、要素一つの配列に格納
        if not isinstance(pagers, list):
            pagers = [pagers]

        # ページ番号(数値)格納用配列
        page_value = []

        last_value = pagers[-1].getText()
        last_value = re.search(r'(\d+)', last_value)
        last_value = int(last_value.group(1))
        debug_print("last_value = ", last_value)

        return last_value

        for page in pagers:
            # 前へ, 1-, 31-等のテキスト部分を文字列取得。
            page = page.getText()
            # debug_print("target page = ", page)
            # 正規表現を使い数値のみ取得("1-" -> 1)
            page = re.search(r'(\d+)', page)
            if page:
                # 番号格納用配列へ追加
                page_value.append(int(page.group(1)))

        # ページャーはBBSの上下にあるため、重複している値を削除（後半部分を削除）        
        half_length = len(page_value) // 2
        page_value = page_value[:half_length]

        # 確認用
        for idx, page in enumerate(page_value):
            debug_print(f"page {idx} = {page}")

        return page_value

    def get_allpages_url(self, top_url, last_page):
        return None

    # 当該ページの全レスを取得する
    def get_allres_inpage(url):
        return None

    # 取得したレスデータをDBへ書き込む
    def insert_table(input_resinfo):
        return None

    def scrape_and_store(self, url):
        # スクレイピング実施
        debug_print("Scraping test. URL = ", url)

        result = self.is_valid_url(url)

        debug_print("isValid = ", result)

        # 対象WebページのTopをスクレイプする
        soup = self.scrape_article_top(url)

        # 記事が存在するかチェック 404でハンドリングできるなら不要？
        # is_exist = self.is_article_exist(soup)

        # 記事タイトルを取得
        title = self.get_title(soup)
        debug_print("title = ["+ title +"]")


        # 記事に取得可能なレスが存在するかチェック
        result = self.is_bbs_exist(soup)
        if result == False:
            debug_print("BBS is not exist.")
            return None

        # 記事の掲示板URL群を取得
        pages = self.get_bbs_length(soup)
        # debug_print("pages = ", pages)
        # 記事の全レスを取得

        # DBへ書き込み




#   <div class="article" id="article">
#     「asdfas」について、まだ記事が書かれていません！
#       <div id="div_article_create">



        return None

    def db_access_sample(self):
        print("DB access test.")

        # SELECT

        qry = "SELECT * FROM websites WHERE id = 1"
        result = self.db.select(qry)
        print("Fetch result = ", result)

        # INSERT

        insert_data = {"name": "test", "url": "https://example.com", "sub_tag1": "B", "sub_tag2": "C", "sub_tag3": "D"}
        qry = "INSERT INTO `websites` (`name`, `url`, `sub_tag1`, `sub_tag2`, `sub_tag3`) VALUES (%(name)s, %(url)s, %(sub_tag1)s, %(sub_tag2)s, %(sub_tag3)s)"
        print("qry = ", qry)
        # self.db.insert(insert_data)

        # qry = "SELECT * FROM websites"
        # result = self.db.select(qry)
        # print("Fetch result = ", result)

        return None

def alchemy_sample(db):
    print("Alchemy test.")

    insert_data = {
        "name": "ALC test",
        "url": "https://alchemy.com",
        "sub_tag1": "A",
        "sub_tag2": "L",
        "sub_tag3": "C"
    }
    db.insert(Website, insert_data)

    filter_condition = and_(Website.name == "desired_name")
    results = db.select(Website, filter_condition)
    print("filter condition =", filter_condition)

    for result in results:
        # print(result)
        print(f"name: {result.name}, url: {result.url}, sub_tag1: {result.sub_tag1}, sub_tag2: {result.sub_tag2}, sub_tag3: {result.sub_tag3}")

    return None


def call_scraping():
    db_uri = 'mysql+pymysql://admin:S8n6F2a!@db_container/nico_db'
    print("db_uri = ", db_uri)
    db = Database(db_uri)
    article_url = "https://dic.nicovideo.jp/a/asdfsdf"
    article_url = "https://dic.nicovideo.jp/a/%E5%86%8D%E7%8F%BE" # 再現
    article_url = "https://dic.nicovideo.jp/a/%E5%9C%9F%E8%91%AC" # 土葬
    article_url = "https://dic.nicovideo.jp/a/%E3%82%A2%E3%83%80%E3%83%AB%E3%83%88%E3%83%93%E3%83%87%E3%82%AA%E3%81%AB%E3%81%8A%E3%81%91%E3%82%8B%E3%83%84%E3%83%83%E3%82%B3%E3%83%9F%E3%81%A9%E3%81%93%E3%82%8D%E3%81%AE%E5%A4%9A%E3%81%84%E5%B1%95%E9%96%8B%E4%B8%80%E8%A6%A7"    # アダルトビデオにおけるツッコミどころの多い展開一覧(67)

    scraper = NicopediScraper(db)
    scraper.scrape_and_store(article_url)

    return None

if __name__ == "__main__":
    print("Called as main.")
    call_scraping()
    
    # db_uri = 'mysql+pymysql://admin:S8n6F2a!@db_container/nico_db'
    # print("db_uri = ", db_uri)
    # db = Database(db_uri)
    # result = alchemy_sample(db)

    # db = Database('db_container', 'admin', 'S8n6F2a!', 'nico_db')
    # scraper = NicopediScraper(db)
    # scraper.db_access_sample()

