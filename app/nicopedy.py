import sys
import os

import requests
from requests.packages.urllib3.util import ssl_

import urllib.request
import ssl

from sympy import fibonacci

from bs4 import BeautifulSoup
import re # 正規表現用
from time import sleep      # 待ち時間用
from sqlalchemy import and_, or_, not_, asc, desc
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
RESPONSES_PER_PAGE = 30  # 1ページあたりの表示数
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

    # 記事IDを取得
    def get_article_id(self, soup):
        article_id = 0
        meta_og_url = soup.find("meta", {"property": "og:url"})

        meta_url = meta_og_url.get("content")
        article_id = meta_url.rsplit('/', 1)[-1]  # URLの最後の部分を取得

        return article_id

    def is_already_scraped(self, article_id):
        debug_print("Func: is_already_scraped(), article_id = ", article_id)
        scraped = False     # 既にスクレイピング済みかどうか True=済み, False=未済
        last_res_no = 0  # 最終レス番号(0 = レス無しまたは未スクレイピング)

        # article_idをキーにDBから記事情報を取得
        filter_condition = ArticleList.article_id == article_id
        result = self.db.select(ArticleList, filter_condition)
        
        matched_records = result.count()
        debug_print("Matched record count = ", matched_records)
        debug_print("fetch result = ", result)
        
        # 既にレコードが存在するかチェックする。

        # 1件発見(正常)
        if matched_records == 1:
            # レコードが存在する場合
            if result[0].last_res_id is not None:
                # スクレイピング済みであれば
                scraped = True
                last_res_no = result[0].last_res_id
            else:
                # スクレイピングがまだであれば
                scraped = False
                last_res_no = 0 # last_res_idにNULLが設定されている場合
        elif matched_records >= 2:
            # レコードが2件以上存在する場合はエラー
            # 異常ケース
            ErrorHandler.handle_error(None, f"Duplicate records found. article_id = {article_id}", PROGRAM_EXIT)
        else:
            # レコードが存在しない場合 = 未走査なら正常
            debug_print("Never scraped. article_id = ", article_id)

        return scraped, last_res_no
    
    # 記事の最終スクレイピングページurlを取得
    def get_last_scraped_page(self, url, last_scraped_id):
        tgt_url = None
        return tgt_url

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
        for page in range(1, last_page + 1, RESPONSES_PER_PAGE):
            generate_url = base_url + f"/{page}-"
            pages.append(generate_url)

        return pages

    # 開始ページ番・最終ページ番から走査対象となるURLリストを生成
    def get_scrape_target_urls(self, article_url, start_page, end_page):

        debug_print("Func: get_scrape_target_urls()")
        debug_print(f"start page = {start_page}, end page = {end_page}")

        if(start_page % RESPONSES_PER_PAGE != 1):
            debug_print("Invalid start_page = ", start_page)
            return None
        if(end_page % RESPONSES_PER_PAGE != 1):
            debug_print("Invalid end_page = ", end_page)
            return None
        
        base_url = article_url
        base_url = base_url.replace('/a/', '/b/a/')

        pages = []

        for page in range(start_page, end_page + 1, RESPONSES_PER_PAGE):
            generate_url = base_url + f"/{page}-"
            pages.append(generate_url)

        return pages

    def get_allres_inarticle(self, url):
        return None

    def get_allres_from_pages(self, page_urls):
        debug_print("Func: get_allres_from_pages()")

        all_res = []

        for idx, page_url in enumerate(page_urls):
            result_single_page = self.get_allres_inpage(page_url)
            debug_print("================")
            debug_print(f"page_url [{idx}] = {page_url}")

            for res_in_page in result_single_page:
                # debug_print("res_in_page = ", res_in_page)
                all_res.append(res_in_page)

            if idx == 3: break
        
        # for idx, res_in_page in enumerate(all_res):
        #     debug_print(f"res_in_page[{idx}] = ", res_in_page)

        return all_res

    def get_allres_inpage(self, page_url):

        debug_print("Func: get_allres_inpage(), page_url = ", page_url)

        ctx = ssl.create_default_context()
        ctx.options |= 0x4

        with urllib.request.urlopen(page_url, context=ctx) as response:
            html_content = response.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        res_heads = soup.find_all("dt", class_="st-bbs_reshead")
        res_bodys = soup.find_all("dd", class_="st-bbs_resbody")

        formatted_Head = []
        formatted_Body = []

        article_detail_list = []

        article_detail_dict = {
            'article_id': None,
            'resno': None,
            'post_name': None,
            'post_date': None,
            'user_id': None,
            'bodytext': None,
            'page_url': None,
            'deleted': None
        }

        for in_idx, res_head in enumerate(res_heads):
            # debug_print("res_head = ", res_head)

            # 記事ID取得（各レスに埋め込まれている値）
            dt_tag = soup.find("dt", {'class': 'st-bbs_reshead'})
            article_id = dt_tag.get('data-article_id')

            # レス番号・投稿者名取得
            bbs_res_no = res_head.find("span", class_="st-bbs_resNo").getText()
            bbs_name = res_head.find("span", class_="st-bbs_name").getText()

            # その他投稿者情報取得
            bbs_res_Info = res_head.find("div", class_="st-bbs_resInfo")

            is_deleted = False

            try:
                # 投稿日時取得
                bbs_res_info_time = bbs_res_Info.find("span", class_="bbs_resInfo_resTime").getText()
                # bbs_res_info_time を日本語の曜日から英語の曜日に変換
                bbs_res_info_time_en = self.convert_jp_weekday_to_en(bbs_res_info_time)
                # 変換後の文字列を datetime オブジェクトに変換
                post_datetime = datetime.strptime(bbs_res_info_time_en, '%Y/%m/%d(%a) %H:%M:%S')
            except ValueError:
                bbs_res_info_time = bbs_res_Info.find("span", class_="bbs_resInfo_resTime").getText()
                post_datetime = None
                is_deleted = True
                # debug_print("Wrong format for datetime: ", bbs_res_info_time)

            # 投稿者ID取得
            bbs_res_info_id = bbs_res_Info.get_text().strip()
            id_text = bbs_res_info_id.split('ID:')[1].strip()
            id_text = id_text.split(' ')[0].strip()

            article_detail_dict = {key: None for key in article_detail_dict}

            article_detail_dict['article_id'] = int(article_id)
            article_detail_dict['resno'] = int(bbs_res_no)
            article_detail_dict['post_name'] = bbs_name
            article_detail_dict['post_date'] = post_datetime
            article_detail_dict['user_id'] = id_text
            article_detail_dict['page_url'] = page_url
            article_detail_dict['deleted'] = is_deleted

            # debug_print("article_detail_dict = ", article_detail_dict)

            article_detail_list.append(article_detail_dict)
      
        for in_idx, res_body in enumerate(res_bodys):
            # debug_print("res_body = ", res_body)

            b = str(res_body)
            b = b.replace('<br>', '\n')
            b = b.replace('<br/>', '\n')
            b = BeautifulSoup(b, 'html.parser').getText()

            b = b.strip()
            b = b.strip('\n')

            # debug_print(f"body text [{in_idx}] :\n"+b)
            article_detail_list[in_idx]['bodytext'] = b

        # スクレイピング間隔を空ける
        # sleep(SCRAPING_INTERVAL)

        # for idx, article_detail in enumerate(article_detail_list):
        #     debug_print(f"art_detail[{idx}] = ", article_detail)


        return article_detail_list

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

    def get_page_number_from_res_id(self, res_id):
        if res_id < 1:
            debug_print("Invalid res_id = ", res_id)
            return -1  # 不正なレス番号
        
        page_number = ((res_id - 1) // RESPONSES_PER_PAGE) * RESPONSES_PER_PAGE + 1
        return page_number

    def get_allrecords_by_article_id(self, article_id):
        
        exiting_res_list = []

        filter_condition = and_(ArticleDetail.article_id == article_id)

        existing_res_list = self.db.select(ArticleDetail, filter_condition).order_by(asc(ArticleDetail.resno))

        return existing_res_list

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

        # 記事IDを取得
        article_id = self.get_article_id(soup)
        debug_print("article_id = ", article_id)

        # 記事に取得可能なレスが存在するかチェック
        result = self.is_bbs_exist(soup)
        if result == False:
            debug_print("BBS is not exist.")
            return None
        
        # 記事が既にスクレイピング済みかチェック。スクレイピング済みであれば最終レス番号を取得。
        scraped, last_id = self.is_already_scraped(article_id)

        # 最後にスクレイピングした記事のページ番号を取得
        # for idx in range(20, 30):
        #     last_id = fibonacci(idx)
        #     last_page = self.get_page_number_from_res_id(last_id)
        #     debug_print(f"last_id = {last_id}, last_page = {last_page}")
        last_got_page = self.get_page_number_from_res_id(last_id)

        # 記事の掲示板URLの最終ページ番号を取得
        last_bbs_page = self.get_bbs_length(soup)

        # 記事タイトルを取得
        title = self.get_title(soup)
        debug_print("title = ["+ title +"]")

        # 今回スクレイピング対象となるページのURLリストを取得
        scrape_targets = self.get_scrape_target_urls(url, last_got_page, last_bbs_page)

        # for scrape_target in scrape_targets:
        #     debug_print("scrape_target = ", scrape_target)

        # 記事の全レスを取得
        # all_res = self.get_allres_inpage(scrape_targets)
        all_res = self.get_allres_from_pages(scrape_targets)

        # len_scraped_data = len(all_res)
        # len_scraped_data -= 1
        # debug_print(f"all_res[{0}] = ", all_res[0])

        # index_30_percent = int(len_scraped_data * 0.3)
        # debug_print(f"all_res[{index_30_percent}] = ", all_res[index_30_percent])

        # index_60_percent = int(len_scraped_data * 0.6)
        # debug_print(f"all_res[{index_60_percent}] = ", all_res[index_60_percent])

        # debug_print(f"all_res[{len_scraped_data}] = ", all_res[len_scraped_data])

        # debug_print('\n'+all_res[0]['bodytext'])
        # debug_print('\n'+all_res[index_30_percent]['bodytext'])
        # debug_print('\n'+all_res[index_60_percent]['bodytext'])
        # debug_print('\n'+all_res[len_scraped_data]['bodytext'])

        # for res in all_res:
        #     debug_print(res['resno'], ':',res['bodytext'], '★')

        all_res = all_res[:10]

        indb_list = self.get_allrecords_by_article_id(article_id)
        idxx = 0
        for res in indb_list:
            idxx += 1
            debug_print(res.article_id, ':',res.resno, ':',res.bodytext[:10], '★')
            if idxx == 10:
                break



        # existing_keys_set = self.db.get_existing_keys(ArticleDetail, ['article_id', 'resno'])
        # debug_print("existing_keys_set = ", existing_keys_set)
        # duplicates = []

        # # 新しいレコードを確認
        # for record in all_res:
        #     new_key = (record['article_id'], record['resno'])
        #     debug_print("new_key = ", new_key)
        #     if new_key in existing_keys_set:
        #         debug_print(f"Duplicate key found: {new_key}")
        #         duplicates.append(new_key)

        # # 重複しているレコードがあれば処理
        # if duplicates:
        #     print(f"Found duplicate keys: {duplicates}")
        #     # 何らかの処理を行う
        # else:
        #     # 重複がなければbulk_insertを実行
        #     debug_print("No duplicate keys found.")
        #     self.db.bulk_insert(ArticleDetail, all_res)

        # DBへ書き込み
        # self.db.bulk_insert(ArticleDetail, all_res)



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
    article_url = "https://dic.nicovideo.jp/a/%E5%9C%9F%E8%91%AC" # 土葬 / レス数30以下サンプル
    article_url = "https://dic.nicovideo.jp/a/Linux"    # Linux / レス数100超えサンプル

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

