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
from dotenv import load_dotenv # .envファイルの読み込み
load_dotenv('../.env') # 環境変数のロード
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")


# Local
# Set import module directory
current_dir = os.path.dirname(os.path.abspath(__file__))
import_dir = os.path.join(current_dir, 'util')
sys.path.append(import_dir)

from models import Website, Config, ArticleList, ArticleDetail
from debug_tools import debug_print
from db_operator import Database
from error_handler import ErrorHandler, PROGRAM_EXIT, PROGRAM_CONTINUE
from date_tools import convert_jp_weekday_to_en



# 掲示板、1Pあたりのレス数
RESPONSES_PER_PAGE = 30  # 1ページあたりの表示数
# スクレイピング間隔(秒)
SCRAPING_INTERVAL = 1
# APIコンテナのURL
API_URL = "http://api_container:8000"

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
        # API_URL = "http://api_container:8000"
        # filter_condition = {"url": targetArtURL}
        # response = requests.get(f"{API_URL}/article_list", params=filter_condition)
        # websites = response.json()

        # if response.status_code == 200:
        #     is_Nicopedi_URL = True
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

    # 記事に取得可能なレスが存在するかチェック
    # レスが無い場合はBBSそのものが存在しない
    def is_bbs_exist(self, soup):
        #  BBSが存在しない場合は「st-pg_contents」クラスが存在しない。マークとなるクラス名はDB内で定義済み。
        return self.is_exist_target_class(soup, "RES NOT EXIST CLASS")

    # 記事内容が存在するページかチェック
    # 「存在しない記事」にのみ存在するクラスを取得
    # "scrape_article_top"でエラーハンドリングできているため不要
    # def is_article_exist(self, soup):
    #     debug_print("Func: is_article_exist()")
    #     return self.is_exist_target_class(soup, "ARTICLE NOT EXIST CLASS")

    # 渡したsoupデータ内に、tagで指定したクラスが存在するかチェック
    def is_exist_target_class(self, soup, tag):
        # tagを手掛かりに、DBからクラス名を取得
        filter_condition = and_(Config.config_type == tag)
        configs = self.db.select(Config, filter_condition)
        config_value = configs[0].value

        # 引っ張ってきたクラスが存在するかチェック（存在する場合はTrueを返す）
        class_exists = soup.find(class_=config_value) != None

        # debug_print(f"Is exists {config_value} ? => {class_exists}")

        return class_exists

    # 記事が既にスクレイピング済みか(DB内に当該記事が存在するか)チェック。スクレイピング済みであれば最終レス番号を取得
    # APIを使ってDBから取得するように変更
    def is_already_scraped(self, article_id):
        debug_print ("Func: is_already_scraped()")

        # article_idをキーにDBから記事情報を取得
        resopnse = requests.get(f"{API_URL}/article_list", params={"article_id": article_id})
        debug_print("resopnse = ", resopnse)

        if resopnse.status_code == 200:
            debug_print("Data exists.")
            scraped = True
        else:
            debug_print("Data not exists.")
            scraped = False

        api_result = resopnse.json()
        matched_records = len(api_result)

        debug_print("api_result = ", api_result, ": matched_records = ", matched_records)

        # 既にレコードが存在するか
        fetched_record = None

        if scraped:
            fetched_record = api_result
            # if api_result['last_res_id'] is not None:
            #     # スクレイピング済みであれば
            #     debug_print("Already scraped. Last res no is ", fetched_record['last_res_id'])
        else:
            debug_print("Never scraped. article_id = ", article_id)

        return fetched_record

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

    # レス番号からページ番号を取得
    def get_page_number_from_res_id(self, res_id):
        # 0以下は1ページ目とする。（未スクレイピング対象であっても、この処理まで来ているということは最低1レスは存在する）
        if res_id < 1:
            res_id = 1
        
        page_number = ((res_id - 1) // RESPONSES_PER_PAGE) * RESPONSES_PER_PAGE + 1
        return page_number

    # BBSの最終ページ番号を取得(最終レス番号は記事TOPページに記載されている)
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

        # 最終ページ番号を返す
        return last_value

    # 開始ページ番・最終ページ番から走査対象となるURLリストを生成
    def get_scrape_target_urls(self, article_url, start_page, end_page):

        debug_print(f"Scraping, start page = {start_page}, end page = {end_page}")

        # 1, 31, 61, ... という形でページ番号が指定されているかチェック
        if(start_page % RESPONSES_PER_PAGE != 1):
            debug_print("Invalid start_page = ", start_page)
            return None
        if(end_page % RESPONSES_PER_PAGE != 1):
            debug_print("Invalid end_page = ", end_page)
            return None
        
        # 掲示板に入るために一部URLを書き換える
        base_url = article_url
        base_url = base_url.replace('/a/', '/b/a/')

        # 走査対象となるURLリストを生成
        pages = []
        for page in range(start_page, end_page + 1, RESPONSES_PER_PAGE):
            generate_url = base_url + f"/{page}-"
            pages.append(generate_url)

        return pages

    # 指定したURL(群)に存在する全レスを取得。
    def get_allres_from_pages(self, page_urls):
        debug_print("Func: get_allres_from_pages()")

        all_res = []

        # 指定した単一URLに存在する全レスを取得。（最大30レス）
        for idx, page_url in enumerate(page_urls):
            debug_print(f"page_url [{idx}] = {page_url}")
            result_single_page = self.get_allres_inpage(page_url)

            # 取得したレスを全レスリストに追加
            for res_in_page in result_single_page:
                all_res.append(res_in_page)
  
        return all_res

    # 指定した単一URLに存在する全レスを取得。
    def get_allres_inpage(self, page_url):

        ctx = ssl.create_default_context()
        ctx.options |= 0x4

        # 対象記事が存在しない場合のハンドリング
        try:
            # 対象ページを取得
            with urllib.request.urlopen(page_url, context=ctx) as response:
                html_content = response.read()
        except urllib.error.HTTPError as e:
            if e.code >= 500:  # サーバーエラー
                debug_print(f"Server error. HTTP status code: {e.code}")
                debug_print("Program will be terminated.")
                exit(1)  # プログラムを終了
            elif e.code >= 400:  # クライアントエラー
                debug_print(f"Client error. HTTP status code: {e.code}")
                debug_print("Program will be terminated.")
                exit(1)  # プログラムを終了
        except urllib.error.URLError as e:
            debug_print(f"URL error. Code: {e.reason}")
            debug_print("Program will be terminated.")
            exit(1)  # プログラムを終了

        soup = BeautifulSoup(html_content, 'html.parser')

        res_heads = soup.find_all("dt", class_="st-bbs_reshead")
        res_bodys = soup.find_all("dd", class_="st-bbs_resbody")

        # 取得したレスデータ群を格納するリスト
        article_detail_list = []

        # 1つのレスについて各種情報を入れる辞書
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

        # 各レス、ヘッダデータを取得
        for in_idx, res_head in enumerate(res_heads):

            # 記事ID取得（各レスに埋め込まれている値。全レスで同一のはず）
            dt_tag = soup.find("dt", {'class': 'st-bbs_reshead'})
            article_id = dt_tag.get('data-article_id')

            # レス番号・投稿者名取得
            bbs_res_no = res_head.find("span", class_="st-bbs_resNo").getText()
            bbs_name = res_head.find("span", class_="st-bbs_name").getText()

            # その他投稿者情報取得
            bbs_res_Info = res_head.find("div", class_="st-bbs_resInfo")

            # "削除されました"フラグ。デフォルトはFalse(削除されていない)
            is_deleted = False

            try:
                # 投稿日時取得
                bbs_res_info_time = bbs_res_Info.find("span", class_="bbs_resInfo_resTime").getText()
                # bbs_res_info_time を日本語の曜日から英語の曜日に変換
                bbs_res_info_time_en = convert_jp_weekday_to_en(bbs_res_info_time)
                # 変換後の文字列を datetime オブジェクトに変換
                post_datetime = datetime.strptime(bbs_res_info_time_en, '%Y/%m/%d(%a) %H:%M:%S')
            except ValueError:
                bbs_res_info_time = bbs_res_Info.find("span", class_="bbs_resInfo_resTime").getText()
                post_datetime = None
                is_deleted = True

            # 投稿者ID取得
            bbs_res_info_id = bbs_res_Info.get_text().strip()
            id_text = bbs_res_info_id.split('ID:')[1].strip()
            id_text = id_text.split(' ')[0].strip()

            # 入手した値を辞書の各要素に格納
            new_article_detail_dict = article_detail_dict.copy()

            new_article_detail_dict['article_id'] = int(article_id)
            new_article_detail_dict['resno'] = int(bbs_res_no)
            new_article_detail_dict['post_name'] = bbs_name
            new_article_detail_dict['post_date'] = post_datetime
            new_article_detail_dict['user_id'] = id_text
            new_article_detail_dict['page_url'] = page_url
            new_article_detail_dict['deleted'] = is_deleted

            article_detail_list.append(new_article_detail_dict)
      
        # 各レス、本文データを取得
        for in_idx, res_body in enumerate(res_bodys):

            b = str(res_body)
            b = b.replace('<br>', '\n')
            b = b.replace('<br/>', '\n')
            b = BeautifulSoup(b, 'html.parser').getText()

            b = b.strip()
            b = b.strip('\n')

            article_detail_list[in_idx]['bodytext'] = b


        # スクレイピング間隔を空ける
        sleep(SCRAPING_INTERVAL)

        # for idx, art_detail in enumerate(article_detail_list):
        #     debug_print(f"{idx} : {article_detail_list[idx]['article_id']} , {article_detail_list[idx]['resno']}")

        # 入手した最大30件のレスデータを返す。（配列に辞書データが入っている）
        return article_detail_list

    # 記事IDをキーにDB(article_detail)から一致するレコードを取得
    def get_allrecords_by_article_id(self, article_id):
        
        filter_condition = and_(ArticleDetail.article_id == article_id)
        existing_res_list = self.db.select(ArticleDetail, filter_condition).order_by(asc(ArticleDetail.resno))

        return existing_res_list

    # 取得したレスデータをDBへ書き込む
    def insert_table(input_resinfo):
        return None

    def scrape_and_store(self, url):
        # スクレイピング実施
        debug_print("Scraping test. URL = ", url)

        # 対象記事は存在するか
        result = self.is_valid_url(url)

        # 記事が存在するかチェック 404でハンドリングできるなら不要？
        # is_exist = self.is_article_exist(soup)

        # 記事リスト情報収集(記事ID・タイトル・URL・最終レス番号・移動済みフラグ・新ID)

        # 対象WebページのTopをスクレイプする
        soup = self.scrape_article_top(url)

        # スクレイプに失敗した場合はプログラム終了。
        if soup == None:
            debug_print("Failed to scrape article top.")
            exit(1)

        # 記事IDを取得
        article_id = self.get_article_id(soup)

        # 記事に取得可能なレスが存在するかチェック
        result = self.is_bbs_exist(soup)
        if result == False:
            debug_print("BBS is not exist.")
            return None
        
        debug_print(f"Fetching ID:{article_id}...")

        # 記事が既にスクレイピング済みかチェック。スクレイピング済みであれば最終レス番号を取得。
        fetched_record = self.is_already_scraped(article_id)

        debug_print("fetched_record = ", fetched_record, type(fetched_record))

        # ここまで取得したList用データを格納する辞書を作成
        # Listにデータが存在しない場合(対象記事が未スクレイピングの場合)
        if fetched_record == None:
            is_scraped = False

            # 記事タイトルを取得
            title = self.get_title(soup)

            article_list_dict = {
                'article_id': article_id,
                'title': title,
                'url': url,
                'last_res_id': 0,
                'moved': False,
                'new_id': -1
            }

        # Listにデータが存在する場合(対象記事が既にスクレイピング済みの場合)
        else:
            is_scraped = True

            article_list_dict = fetched_record
            # article_list_dict = {
            #     'article_id': article_id,
            #     'title': fetched_record.title,
            #     'url': fetched_record.url,
            #     'last_res_id': fetched_record.last_res_id,
            #     'moved': fetched_record.moved,
            #     'new_id': fetched_record.new_id
            # }

        debug_print("Data of article_list_dict = ", article_list_dict)

        # 最後にスクレイピングした記事のページ番号を取得
        # for idx in range(20, 30):
        #     last_id = fibonacci(idx)
        #     last_page = self.get_page_number_from_res_id(last_id)
        #     debug_print(f"last_id = {last_id}, last_page = {last_page}")
        last_got_page = self.get_page_number_from_res_id(article_list_dict['last_res_id'])

        # 記事の掲示板URLの最終ページ番号を取得
        last_bbs_page = self.get_bbs_length(soup)

        # 今回スクレイピング対象となるページのURLリストを取得
        scrape_targets = self.get_scrape_target_urls(url, last_got_page, last_bbs_page)

        # 記事の全レスを取得
        all_res = self.get_allres_from_pages(scrape_targets)

        # article_detailテーブルから、対象記事の全レスを取得。
        indb_list = self.get_allrecords_by_article_id(article_id)

        # 「新たに取得したレスデータ群」と「既にDBに入っているレスデータ群」を比較し、重複レコードを除外する。
        # article_idをキーに抽出したデータ群のresnoと比較する。

        # indb_listからレス番号を抽出し、別リスト化。
        indb_resnos = [res.resno for res in indb_list]
        # レス番号が重複している(既にDB内に存在している)レコードを重複レコードとして別リスト化。
        duplicates = [res for res in all_res if res['resno'] in indb_resnos]
        # レス番号が重複していないレコードを別リスト化。（all_res配列を上書きする）
        new_insert = [res for res in all_res if res['resno'] not in indb_resnos]

        # debug_print ("all_res = ", all_res)
        # debug_print ("indb_resnos = ", indb_resnos)

        # 重複レコード出力
        for res in duplicates:
            debug_print("DUPLICATED:", res['article_id'], ':',res['resno'], ':',res['bodytext'][:10], '★')
        # 非重複レコード出力(DBへの書き込み対象)
        for res in new_insert:
            debug_print("NEW INSERT:", res['article_id'], ':',res['resno'], ':',res['bodytext'][:10], '★')

        # new_insertが空の場合(挿入すべき新しい書き込みがない)は処理終了
        if len(new_insert) == 0:
            debug_print("No data for new insert.")
            return None
        # 記事リスト(Article_list)に挿入するため、最新のレス番号を取得する。
        else:
            last_resno = new_insert[-1]['resno']
            article_list_dict['last_res_id'] = last_resno

        # DBへ書き込み
        # 既にスクレイピング済みの場合(記事リストにレコードが存在する場合)はUPDATE
        if is_scraped:
            debug_print("Updating existing record.")
            filter = (ArticleList.article_id == article_id)
            update_data = {
                'last_res_id': article_list_dict['last_res_id'],
                'moved': article_list_dict['moved'],
                'new_id': article_list_dict['new_id']
            }
            # self.db.update(ArticleList, filter, update_data)
        
        # 未スクレイピングの場合(記事リストにレコードが存在しない場合)はINSERT
        else:
            debug_print("Inserting new record.")
            # self.db.insert(ArticleList, article_list_dict)

        # self.db.bulk_insert(ArticleDetail, new_insert)

        return None

        # article_listへのデータ挿入    
            # id INT AUTO_INCREMENT PRIMARY KEY,
            # article_id INT,
            # title VARCHAR(255) NOT NULL,
            # url VARCHAR(255) NOT NULL,
            # last_res_id INT,
            # moved BOOLEAN,
            # new_id INT
        def insert_article_list(self, article_list):
            return None

        # article_detailへのデータ挿入
            # article_id INT NOT NULL,
            # resno INT NOT NULL,
            # post_name VARCHAR(255),
            # post_date DATETIME,
            # user_id VARCHAR(255),
            # bodytext TEXT,
            # page_url VARCHAR(255),
            # deleted BOOLEAN,
            # PRIMARY KEY (article_id, resno)
        def insert_article_detail(self, article_detail):
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

    # << Trial functions ========================================================================

    # ScraperコンテナからAPIコンテナのAPI呼び出しテスト
    def api_access_sample(self):
        print("API access test.")

        article_id = 430509
        response = requests.get(f"{API_URL}/article_list", params={"article_id": article_id})
        api_result = response.json()
        if response.status_code == 200:
            debug_print(api_result)
        
        # レコードが存在するかチェック
        if api_result:
            debug_print("Record is exist")
        else:
            debug_print("Record is not exist")

        # exit(1)
        return None

    def api_delete_article_sample(self):
        print("API delete article test.")

        article_id = 12436  # 削除したい記事のID

        endPointURL = f"{API_URL}/article_list/{article_id}"

        # DELETEリクエストを送信
        response = requests.delete(endPointURL)

        # レスポンス結果を確認
        if response.status_code == 200:
            print("Delete successful")
        else:
            print("Error:", response.status_code, response.text)

        return None

    def api_update_article_sample(self):
        print("API update article test.")

        article_id = 12436
        update_data = {"last_res_id": 20030}

        endPointURL = f"{API_URL}/article_list/{article_id}"

        response = requests.put(endPointURL, json=update_data)

        if response.status_code == 200:
            api_result = response.json()
            print("Update successful:", api_result)
        else:
            print("Error:", response.status_code, response.text)

        return None

    def api_insert_article_sample(self):
        print("API insert article test.")
        
        # 送信する記事データのダミーを作成
        article_data = {
            "article_id": 12436,
            "title": "サンプルタイトル",
            "url": "http://example.com/sample-article",
            "last_res_id": 123,
            "moved": False,
            "new_id": 456
        }

        endPointURL = f"{API_URL}/article_list"

        debug_print("endPointURL = ", endPointURL)
        
        # POSTリクエストを送信
        response = requests.post(endPointURL, json=article_data)

        # レスポンス結果を確認
        if response.status_code == 200:
            api_result = response.json()
            print("Insert successful:", api_result)
        else:
            print("Error:", response.status_code, response.text)

        
        return None

    def api_insert_article_details_sample(self):
        print("API insert article details test.")
        API_URL = "http://api_container:8000"

        # テスト用の記事詳細データを作成
        article_details_data = [
            {
                "article_id": 12436,
                "resno": 1,
                "post_name": "テストユーザー1",
                "post_date": "2022-01-01T12:00:00",
                "user_id": "user123",
                "bodytext": "これはテストコメントです。",
                "page_url": "http://example.com/page1",
                "deleted": False
            },
            {
                "article_id": 1334,
                "resno": 34,
                "post_name": "テストユーザー2",
                "post_date": "2022-01-01T12:00:00",
                "user_id": "usersss",
                "bodytext": "これはテストコメントです。",
                "page_url": "http://example.com/page1",
                "deleted": False
            },
            {
                "article_id": 11446,
                "resno": 1,
                "post_name": "テストユーザー3",
                "post_date": "2022-01-01T12:00:00",
                "user_id": "userbbb",
                "bodytext": "これはテストコメントです。",
                "page_url": "http://example.com/page1",
                "deleted": False
            },
            # 他のレコードも同様に追加
        ]

        endPointURL = f"{API_URL}/article_details"

        # POSTリクエストを送信
        response = requests.post(endPointURL, json=article_details_data)

        # レスポンス結果を確認
        if response.status_code == 200:
            print("Insert successful")
        else:
            print("Error:", response.status_code, response.text)

        return None


    # Trial functions >> ========================================================================

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


def call_scraping(article_title):
    db_uri = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@db_container/{MYSQL_DATABASE}'
    print("db_uri = ", db_uri)
    db = Database(db_uri)

    # URLを生成
    article_url = f"https://dic.nicovideo.jp/a/{article_title}"

    # article_url = "https://dic.nicovideo.jp/a/%E5%86%8D%E7%8F%BE" # 再現 / レス数0サンプル
    # article_url = "https://dic.nicovideo.jp/a/%E5%9C%9F%E8%91%AC" # 土葬 / レス数30以下サンプル
    # article_url = "https://dic.nicovideo.jp/a/asdfsdf"  # 存在しない記事
    # article_url = "https://dic.nicovideo.jp/a/Linux"    # Linux / レス数100超えサンプル・DB登録済み
    # article_url = "https://dic.nicovideo.jp/a/Ubuntu"    # Ubuntu / DB登録済み

    scraper = NicopediScraper(db)

    # scraper.api_access_sample()
    # scraper.api_insert_article_sample()
    # scraper.api_update_article_sample()
    # scraper.api_delete_article_sample()

    scraper.api_insert_article_details_sample()
    exit(0)

    debug_print("Scraping test. URL = ", article_url)

    scraper.scrape_and_store(article_url)

    return None

if __name__ == "__main__":
    print("Called as main.")
    if len(sys.argv) > 1:
        article_title = sys.argv[1]
        call_scraping(article_title)
    else:
        print("No article title provided. Exiting program.")
        sys.exit(1)
    
    # db_uri = 'mysql+pymysql://admin:S8n6F2a!@db_container/nico_db'
    # print("db_uri = ", db_uri)
    # db = Database(db_uri)
    # result = alchemy_sample(db)

    # db = Database('db_container', 'admin', 'S8n6F2a!', 'nico_db')
    # scraper = NicopediScraper(db)
    # scraper.db_access_sample()

