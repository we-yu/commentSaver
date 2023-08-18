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
from datetime import datetime

# Local
# Set import module directory
current_dir = os.path.dirname(os.path.abspath(__file__))
import_dir = os.path.join(current_dir, 'util')
sys.path.append(import_dir)

from debug_tools import debug_print
from db_operator import Database
from models import Website, Config, ArticleList, ArticleDetail
from error_handler import ErrorHandler, PROGRAM_EXIT, PROGRAM_CONTINUE

# 掲示板、1Pあたりのレス数
RES_IN_SINGLEPAGE = 30
# スクレイピング間隔(秒)
SCRAPING_INTERVAL = 5

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
    
    # 対象URLからスクレイピングデータの取得、ページが存在しない場合はメッセージ表示して終了
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

    # 記事内容が存在するページかチェック
    # 「存在しない記事」にのみ存在するクラスを取得
    # "scrape_article_top"でエラーハンドリングできているため不要
    # def is_article_exist(self, soup):
    #     debug_print("Func: is_article_exist()")
    #     return self.is_exist_target_class(soup, "ARTICLE NOT EXIST CLASS")

    # 記事に取得可能なレスが存在するかチェック
    # レスが無い場合はBBSそのものが存在しない
    def is_bbs_exist(self, soup):
        debug_print("Func: is_bbs_exist()")
        #  BBSが存在しない場合は「st-pg_contents」クラスが存在しない。マークとなるクラス名はDB内で定義済み。
        return self.is_exist_target_class(soup, "RES NOT EXIST CLASS")

    # 渡したsoupデータ内に、tagで指定したクラスが存在するかチェック
    def is_exist_target_class(self, soup, tag):
        debug_print("Func: is_exist_target_class(), tag = ", tag)

        # tagを手掛かりに、DBからクラス名を取得
        filter_condition = and_(Config.config_type == tag)
        configs = self.db.select(Config, filter_condition)
        config_value = configs[0].value

        # 引っ張ってきたクラスが存在するかチェック（存在する場合はTrueを返す）
        class_exists = soup.find(class_=config_value) != None

        debug_print(f"Is exists {config_value} ? => {class_exists}")

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
        
        # st-pg_contents下にあるaタグを取得
        pagers = soup.select("div.st-pg_contents > a")
        # debug_print("pagers = ", pagers)

        # 取得した要素が一つだけ(レス数が30以下)だった場合、要素一つの配列に格納
        if not isinstance(pagers, list):
            pagers = [pagers]

        # ページャーの最後の要素を取得(必要なのは最後のページ番号のみ)
        last_value = pagers[-1].getText()

        # 要素から数値のみを取得
        last_value = re.search(r'(\d+)', last_value)
        last_value = int(last_value.group(1))

        debug_print("last_value = ", last_value)

        # 最終ページ番号を返す
        return last_value

        # ページ番号(数値)格納用配列
        page_value = []

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

    # 最終ページ番号・記事トップURLから走査対象となるURLリストを生成
    def get_allpages_url(self, top_url, last_page):
        pages = []

        base_url = top_url
        base_url = base_url.replace('/a/', '/b/a/')

        # https://dic.nicovideo.jp/b/a/linux/151- というフォーマットのURLを生成
        for page in range(1, last_page + 1, RES_IN_SINGLEPAGE):
            generate_url = base_url + f"/{page}-"
            pages.append(generate_url)

        return pages

    # 当該ページの全レスを取得する
    def get_allres_inpage(self, page_urls):
        # ctx = ssl.create_default_context()
        # ctx.options |= 0x4
        # # 対象記事が存在しない場合のハンドリング
        # try:
        #     with urllib.request.urlopen(url, context=ctx) as response:
        #         web_content = response.read()
        #     soup = BeautifulSoup(web_content, "html.parser")        

        ctx = ssl.create_default_context()
        ctx.options |= 0x4

        for idx, page_url in enumerate(page_urls):
            debug_print(f"page_url [{idx}] = {page_url}")

            with urllib.request.urlopen(page_url, context=ctx) as response:
                html_content = response.read()

            # html.parserでパーサーを指定してBeautifulSoupで解析
            soup = BeautifulSoup(html_content, 'html.parser')

            res_heads = soup.find_all("dt", class_="st-bbs_reshead")
            res_bodys = soup.find_all("dd", class_="st-bbs_resbody")

            formatted_Head = []
            formatted_Body = []

            for in_idx, res_head in enumerate(res_heads):
                debug_print("================================")
                # debug_print("res_head = ", res_head)

                # レス番号・投稿者名取得
                bbs_res_no = res_head.find("span", class_="st-bbs_resNo").getText()
                bbs_name = res_head.find("span", class_="st-bbs_name").getText()

                # その他投稿者情報取得
                bbs_res_Info = res_head.find("div", class_="st-bbs_resInfo")

                # 投稿日時取得
                bbs_res_info_time = bbs_res_Info.find("span", class_="bbs_resInfo_resTime").getText()
                # bbs_res_info_time を日本語の曜日から英語の曜日に変換
                bbs_res_info_time_en = self.convert_jp_weekday_to_en(bbs_res_info_time)
                # 変換後の文字列を datetime オブジェクトに変換
                post_datetime = datetime.strptime(bbs_res_info_time_en, '%Y/%m/%d(%a) %H:%M:%S')

                # 投稿者ID取得
                bbs_res_info_id = bbs_res_Info.get_text().strip()
                id_text = bbs_res_info_id.split('ID:')[1].strip()
                id_text = id_text.split(' ')[0].strip()

                # debug_print("bbs_res_no = ", bbs_res_no)
                # debug_print("bbs_name = ", bbs_name)
                # debug_print ("bbs_res_info_time = ", post_datetime.date(), post_datetime.strftime("%a"), post_datetime.time())
                # debug_print("id_text = ", id_text)

                if in_idx == 3:
                    break
            
            for in_idx, res_body in enumerate(res_bodys):
                debug_print("================================")
                # debug_print("res_body = ", res_body)

                b = str(res_body)
                b = b.replace('<br>', '\n')
                b = b.replace('<br/>', '\n')
                b = BeautifulSoup(b, 'html.parser').getText()

                b = b.strip()
                b = b.strip('\n')

                debug_print("body text :\n"+b)  

                if in_idx == 15:
                    break

            # スクレイピング間隔を空ける
            # sleep(SCRAPING_INTERVAL)

        return None

    def convert_jp_weekday_to_en(self, date_str):
        weekdays_jp_to_en = {
            '(日)': '(Sun)',
            '(月)': '(Mon)',
            '(火)': '(Tue)',
            '(水)': '(Wed)',
            '(木)': '(Thu)',
            '(金)': '(Fri)',
            '(土)': '(Sat)'
        }
        
        for jp, en in weekdays_jp_to_en.items():
            date_str = date_str.replace(jp, en)
        return date_str



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

        # 記事の掲示板URLの最終ページ番号を取得
        last_page = self.get_bbs_length(soup)

        # 取得対象となる掲示板レスのURLリストを取得
        all_page_urls = self.get_allpages_url(url, last_page)

        # for page_url in all_page_urls:
        #     debug_print("page_url = ", page_url)

        # 記事の全レスを取得
        all_res = self.get_allres_inpage(all_page_urls)

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
    article_url = "https://dic.nicovideo.jp/a/asdfsdf"  # 存在しない記事
    article_url = "https://dic.nicovideo.jp/a/%E5%86%8D%E7%8F%BE" # 再現 / レス数0サンプル
    article_url = "https://dic.nicovideo.jp/a/Linux"    # Linux / レス数100超えサンプル
    article_url = "https://dic.nicovideo.jp/a/%E5%9C%9F%E8%91%AC" # 土葬 / レス数30以下サンプル

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

