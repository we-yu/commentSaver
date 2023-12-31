import sys
import os

import requests
from urllib.parse import quote
import urllib.request
import ssl

# from sympy import fibonacci

from bs4 import BeautifulSoup
import re # 正規表現用
from time import sleep      # 待ち時間用
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

# from models import Website, Config, ArticleList, ArticleDetail
from debug_tools import debug_print
from db_operator import Database
from error_handler import ErrorHandler, PROGRAM_EXIT, PROGRAM_CONTINUE
from date_tools import convert_jp_weekday_to_en
from api_db_access import API_DB_Access


# 掲示板、1Pあたりのレス数
RESPONSES_PER_PAGE = 30  # 1ページあたりの表示数
# スクレイピング間隔(秒)
SCRAPING_INTERVAL = 1
# APIコンテナのURL
API_URL = "http://api_container:8000"

class NicopediScraper:
    def __init__(self, db):
        self.db = db
        self.api_db_access = API_DB_Access(API_URL)

    # 対象が適正なニコ記事かどうかチェック.
    def is_valid_url(self, targetArtURL):
        debug_print(f"Func: is_valid_url(), arg = {targetArtURL}")

        response = self.api_db_access.read_website_by_name("Niconico")
        if response.status_code != 200:
            debug_print("Failed to get website data.")
            return False
        website_data = response.json()
        nico_url = website_data['url']
        is_Nicopedi_URL = targetArtURL.startswith(nico_url)

        return is_Nicopedi_URL
    
    # 対象URLからスクレイピングデータの取得、ページが存在しない場合はメッセージ表示して終了
    def scrape_article_top(self, url):
        debug_print(f"Func: scrape_article_top(), arg = {url}")

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
            ErrorHandler.handle_error(e, f"HTTP error occurred CODE: {e.code}", PROGRAM_EXIT)
            return None
        except urllib.error.URLError as e:
            ErrorHandler.handle_error(e, f"URL error occurred REASON: {e.reason}", PROGRAM_EXIT)
            return None
        ####################################################
        return soup

    # 記事IDを取得
    def get_article_id(self, soup):
        meta_og_url = soup.find("meta", {"property": "og:url"})
        if meta_og_url is None:
            debug_print("Meta og:url tag not found.")
            return None  # または適切なエラーハンドリング

        meta_url = meta_og_url.get("content")
        article_id = meta_url.rsplit('/', 1)[-1]  # URLの最後の部分を取得

        debug_print(f"Func: get_article_id(), article_id = {article_id}")
        return article_id

    # 記事に取得可能なレスが存在するかチェック
    # レスが無い場合はBBSそのものが存在しない
    def is_bbs_exist(self, soup):
        #  BBSが存在しない場合は「st-pg_contents」クラスが存在しない。マークとなるクラス名はDB内で定義済み。
        return self.is_exist_target_class(soup, "RES NOT EXIST CLASS")

    # 渡したsoupデータ内に、tagで指定したクラスが存在するかチェック
    def is_exist_target_class(self, soup, tag):
        debug_print(f"Func: is_exist_target_class(), tag = {tag}")

        # tagを手掛かりに、DBからクラス名を取得
        config_data = self.api_db_access.read_config_by_type(tag)
        if not config_data:
            debug_print("Failed to get config data :", tag)
            return None

        config_value = config_data['value']

        # 引っ張ってきたクラスが存在するかチェック（存在する場合はTrueを返す）
        class_exists = soup.find(class_=config_value) != None
        # debug_print(f"Is exists {config_value} ? => {class_exists}")

        return class_exists

    # 記事が既にスクレイピング済みか(DB内に当該記事が存在するか)チェック。スクレイピング済みであれば最終レス番号を取得
    # APIを使ってDBから取得するように変更
    def is_already_scraped(self, article_id):
        debug_print (f"Func: is_already_scraped(), article_id = {article_id}")

        # article_idをキーにDBから記事情報を取得
        response = self.api_db_access.read_article_list_by_id(article_id)
        # debug_print("response = ", response)

        if response.status_code == 200:
            # debug_print("Data exists.")
            scraped = True
        else:
            # debug_print("Data not exists.")
            scraped = False


        # 既にレコードが存在するか
        fetched_record = None

        if scraped:
            api_result = response.json()

            # matched_records = len(api_result)
            # debug_print("api_result = ", api_result, ": matched_records = ", matched_records)

            fetched_record = api_result

            # if api_result['last_res_id'] is not None:
            #     # スクレイピング済みであれば
            #     debug_print("Already scraped. Last res no is ", fetched_record['last_res_id'])
        else:
            debug_print("<<Never scraped>>")

        return fetched_record

    # 記事が移動済みかチェック。移動済みであれば新IDを取得
    def check_redirect(self, soup):
        # リダイレクトの確認を行う関数
        debug_print("Func: check_redirect()")

        # 'http-equiv'が'refresh'であるmetaタグを探す
        meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
        if not meta_refresh:
            # http-equiv='refresh'を持つmetaタグがない場合、リダイレクトは存在しない
            return False, None

        # content属性を取得
        refresh_content = meta_refresh.get('content', '').lower()
        url_split = refresh_content.split('url=')
        if len(url_split) < 2:
            # 'url='が見つからない場合の処理
            debug_print("リフレッシュメタタグのcontent属性に'url='が含まれていません。")
            return False, None

        # 'url='が見つかった場合、contentを分割してURL部分を取得
        url_part = url_split[1]
        new_url = url_part.split(';')[0].strip() if ';' in url_part else url_part.strip()
        return True, new_url


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

        # 大百科仕様変更への対応
        article_title = article_title.find('a', class_='self_link')

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
        debug_print(f"Func: get_scrape_target_urls(), args = {article_url}, {start_page}, {end_page}")

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
                post_datetime = post_datetime.isoformat()
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
        debug_print(f"Func: get_allrecords_by_article_id(), arg = {article_id}")

        existing_res_list = self.api_db_access.select_article_details(article_id)

        return existing_res_list

    # 取得したレスデータをDBへ書き込む
    def insert_table(input_resinfo):
        return None

    def scrape_and_store(self, url):
        debug_print("Func: scrape_and_store()")

        # URLをエンコード(タイトルが日本語の場合はエンコードしないとエラーになる)
        encoded_url = quote(url, safe='/:?=&')
        debug_print("Scraping target URL = ", url, "encoded_url = ", encoded_url)

        url = encoded_url

        # スクレイピング実施
        
        # 対象がニコニコ大百科のURLかをチェック
        result = self.is_valid_url(url)
        if result == False:
            debug_print("Invalid URL.")
            return None

        # 記事リスト情報収集(記事ID・タイトル・URL・最終レス番号・移動済みフラグ・新ID)

        # 対象WebページのTopをスクレイプする
        soup = self.scrape_article_top(url)
        # スクレイプに失敗した場合はプログラム終了。
        if soup == None:
            debug_print("Failed to scrape article top.")
            exit(1)

        # リダイレクト有無をチェック
        is_redirected, new_url = self.check_redirect(soup)
        
        # リダイレクトされた場合は終了
        if is_redirected:
            redirected = True
            debug_print('This article has been redirected.')
            debug_print("New URL = ", new_url)
            sys.exit(0)

        # 記事IDを取得
        article_id = self.get_article_id(soup)
        if article_id == None:
            debug_print("Failed to get article ID.")
            exit(1)

        article_id = int(article_id)

        # 記事に取得可能なレスが存在するかチェック
        result = self.is_bbs_exist(soup)
        if result == False:
            debug_print("BBS is not exist.")
            return None
        
        debug_print(f"Fetching article's ID :{article_id}...")

        # 記事が既にスクレイピング済みかチェック。スクレイピング済みであれば最終レス番号を取得。
        fetched_record = self.is_already_scraped(article_id)

        # debug_print("fetched_record = ", fetched_record, type(fetched_record))

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
                'new_article_title': None
            }

            # 新たに挿入する記事のタイトルを表示
            debug_print(f"New article, name is <{title}>")

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
            #     'new_article_title': fetched_record.new_article_title
            # }

            # 既にスクレイピング済みの記事のタイトルを表示
            debug_print(f"Existing article, name is <{article_list_dict['title']}>")

        debug_print("Currently data of article_list_dict = ", article_list_dict)

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

        # for each_url in scrape_targets:
        #     debug_print("Scraping target URL = ", each_url)
    
        # 記事の全レスを取得
        all_res = self.get_allres_from_pages(scrape_targets)

        # 新規記事の場合、indb_list(DBに存在するデータ)は存在せず、空白となる。
        # 既存記事の場合、article_detailテーブルから記事IDに合致する全レコードを引っ張り、indb_list(DBに存在するデータ)に設定する。

        indb_list = []

        if is_scraped:
            # article_detailテーブルから、対象記事の全レスを取得。
            response = self.get_allrecords_by_article_id(article_id)

            if response.status_code == 200:
                # detailテーブルからの取得が成功したなら既にDBに存在するレコードを取得
                indb_list = response.json()
            else:
                # detailテーブルからの取得が失敗したならindb_listは空にする。
                indb_list = []
                # 異常ケースのため、警告ログ表示。
                debug_print("Article is existing. But failed to get records from detail table.")
            
        # 「新たに取得したレスデータ群」と「既にDBに入っているレスデータ群」を比較し、重複レコードを除外する。
        # article_idをキーに抽出したデータ群のresnoと比較する。

        # indb_listからレス番号を抽出し、別リスト化。
        indb_resnos = [record['resno'] for record in indb_list]
        # レス番号が重複している(既にDB内に存在している)レコードを重複レコードとして別リスト化。
        duplicates = [res for res in all_res if res['resno'] in indb_resnos]
        # レス番号が重複していないレコードを別リスト化。（all_res配列を上書きする）
        new_insert = [res for res in all_res if res['resno'] not in indb_resnos]

        # 重複レコード出力
        if duplicates:
            debug_print("DUPLICATED:", duplicates[0]['article_id'], ':', duplicates[0]['resno'], ':', duplicates[0]['bodytext'][:10], '★')
            if len(duplicates) > 1:  # 1件以上ある場合のみ最後のレコードを表示
                debug_print("DUPLICATED:", duplicates[-1]['article_id'], ':', duplicates[-1]['resno'], ':', duplicates[-1]['bodytext'][:10], '★')

        # 非重複レコード出力(DBへの書き込み対象)
        if new_insert:
            debug_print("NEW INSERT:", new_insert[0]['article_id'], ':', new_insert[0]['resno'], ':', new_insert[0]['bodytext'][:10], '★')
            if len(new_insert) > 1:  # 1件以上ある場合のみ最後のレコードを表示
                debug_print("NEW INSERT:", new_insert[-1]['article_id'], ':', new_insert[-1]['resno'], ':', new_insert[-1]['bodytext'][:10], '★')

        # for res in duplicates:
        #     debug_print("DUPLICATED:", res['article_id'], ':',res['resno'], ':',res['bodytext'][:10], '★')
        # 非重複レコード出力(DBへの書き込み対象)
        # for res in new_insert:
        #     debug_print("NEW INSERT:", res['article_id'], ':',res['resno'], ':',res['bodytext'][:10], '★')

        # new_insertが空の場合(挿入すべき新しい書き込みがない)は処理終了
        if len(new_insert) == 0:
            debug_print("No data for new insert.")
            return None
        
        # 記事リスト(Article_list)に挿入するため、最新のレス番号を取得する。
        last_resno = new_insert[-1]['resno']
        article_list_dict['last_res_id'] = last_resno

        # DBへ書き込み
        # 既にスクレイピング済みの場合(記事リストにレコードが存在する場合)はUPDATE
        if is_scraped:
            debug_print("Updating existing record.")
            # filter = (ArticleList.article_id == article_id)
            update_data = {
                'last_res_id': article_list_dict['last_res_id'],
                'moved': article_list_dict['moved'],
                'new_article_title': article_list_dict['new_article_title']
            }
            # debug_print("update_data = ", update_data)
            # self.db.update(ArticleList, filter, update_data)
            self.api_db_access.update_article_list(article_id, update_data)
        
        # 未スクレイピングの場合(記事リストにレコードが存在しない場合)はINSERT
        else:
            debug_print("Inserting new record =", article_list_dict)
            # self.db.insert(ArticleList, article_list_dict)
            self.api_db_access.create_article_list(article_list_dict)

        # self.db.bulk_insert(ArticleDetail, new_insert)

        debug_print("Inserting new records for Detail, record length is ", len(new_insert))
        self.api_db_access.insert_article_details(new_insert)

        return None

    def create_article_list(self, article_list_dict):
        debug_print("Func: create_article_list()")
        endPointURL = f"{API_URL}/article_list"
        response = requests.post(endPointURL, json=article_list_dict)
        res = response.status_code
        return res



def call_scraping(article_title):
    debug_print("Func: call_scraping()")
    db_uri = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@db_container/{MYSQL_DATABASE}'
    # debug_print("db_uri = ", db_uri)
    db = Database(db_uri)

    # URLを生成
    article_url = f"https://dic.nicovideo.jp/a/{article_title}"

    # article_url = "https://dic.nicovideo.jp/a/%E5%86%8D%E7%8F%BE" # 再現 / レス数0サンプル
    # article_url = "https://dic.nicovideo.jp/a/%E5%9C%9F%E8%91%AC" # 土葬 / レス数30以下サンプル
    # article_url = "https://dic.nicovideo.jp/a/asdfsdf"  # 存在しない記事
    # article_url = "https://dic.nicovideo.jp/a/Linux"    # Linux / レス数100超えサンプル・DB登録済み
    # article_url = "https://dic.nicovideo.jp/a/Ubuntu"    # Ubuntu / DB登録済み

    scraper = NicopediScraper(db)

    # scraper.test_api_access()
    # scraper.api_db_access.test_create_article()
    # scraper.api_db_access.test_update_article()
    # scraper.api_db_access.test_delete_article()

    # scraper.api_db_access.test_create_article_details()
    # response = scraper.api_db_access.api_read_article_details_sample(4567890)

    # exit(0)

    scraper.scrape_and_store(article_url)

    return None

if __name__ == "__main__":
    debug_print("Called as main.")
    if len(sys.argv) > 1:
        article_title = sys.argv[1]
        call_scraping(article_title)
    else:
        debug_print("No article title provided. Exiting program.")
        sys.exit(1)
    debug_print("Program end.")