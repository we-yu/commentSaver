import sys
from urllib.parse import quote
import urllib.request
import ssl
from bs4 import BeautifulSoup
from time import sleep
import re # 正規表現用
from datetime import datetime

# Local
from app.common.api_db_access import API_DB_Access
import app.common.settings

from common_utils import CommonUtils
from debug_tools import debug_print
from date_tools import convert_jp_weekday_to_en
from error_handler import ErrorHandler, PROGRAM_EXIT, PROGRAM_CONTINUE

# 掲示板、1Pあたりのレス数
RESPONSES_PER_PAGE = 30  # 1ページあたりの表示数
# スクレイピング間隔(秒)
SCRAPING_INTERVAL = 1

# 必要に応じて他のインポートを追加する
# 例えば:
# from models import ArticleDetail
# from db_operator import Database

class DetailController:
    def __init__(self, api_url):
        self.api_db_access = API_DB_Access(api_url)

    def detail_controller_main(self):
        debug_print("Func: detail_controller_main()")

        # article_listの取得
        result = self.api_db_access.read_all_article_list()

        if result is None:
            # エラー処理
            debug_print("Error: Failed to get article list")
            return PROGRAM_EXIT
        
        # listをベースにループ実装
        for article in result:

            # Debug
            if article['title'] != "オールひろゆき":
                # https://dic.nicovideo.jp/a/%E3%82%AA%E3%83%BC%E3%83%AB%E3%81%B2%E3%82%8D%E3%82%86%E3%81%8D
                continue

            # article_listの一覧に沿って、スクレイピングを実行する
            # スクレイピング及びDB更新処理呼び出し
            # debug_print("article: {}".format(article))
            debug_print(f"Article title and URL = {article['title']}, {article['url']}")

            self.scrape_and_store(article)

            # スクレイピング及びDB更新処理呼び出し

        return None

    def scrape_and_store(self, article_data):
        debug_print("Func: scrape_and_store(), article title is ", article_data["title"])
        # データをスクレイピングして保存するメインの処理

        # debug_print("Call util func = ", CommonUtils.sample_common_utils("test"))
        
        # 記事TOPのURLを取得し、スクレイピングを実行
        top_url = article_data["url"]
        soup = CommonUtils.scrape_article_top(top_url)


        # リダイレクトチェック
        # リダイレクトされた場合は終了
        is_redirected, new_url = CommonUtils.check_redirect(soup)
        if is_redirected:
            redirected = True
            debug_print(f"This article has been redirected. Processing will be terminated.")
            return None

        result = self.is_exist_target_class(soup, "RES NOT EXIST CLASS")
        if result == None:
            debug_print("BBS is not exist.")
            return None
        
        # debug_print('article_data = ', article_data)

        article_list_dict = article_data

        last_got_page = self.get_page_number_from_res_id(article_list_dict['last_res_id'])
        debug_print(f"last_got_page = {last_got_page}", indent=4)
        last_bbs_page = self.get_bbs_length(soup)
        debug_print(f"last_bbs_page = {last_bbs_page}", indent=4)
        scrape_targets = self.get_scrape_target_urls(top_url, last_got_page, last_bbs_page)

        for scrape_target in scrape_targets:
            debug_print(f"scrape_target = {scrape_target}", indent=4, short=True)
        
        all_res = self.get_allres_from_pages(scrape_targets)

        indb_list = []

        # article_detailテーブルから、対象記事の全レスを取得。
        response = self.get_allrecords_by_article_id(article_list_dict['article_id'])

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

        # new_insertが空の場合(挿入すべき新しい書き込みがない)は処理終了
        if len(new_insert) == 0:
            debug_print("No data for new insert.")
            return None
        
        # 記事リスト(Article_list)に挿入するため、最新のレス番号を取得する。
        debug_print("article_list_dict = ", article_list_dict)
        last_resno = new_insert[-1]['resno']
        article_list_dict['last_res_id'] = last_resno

        # article_listテーブルの更新
        debug_print("Update article_list table.")
        update_data = {
            'last_res_id': article_list_dict['last_res_id'],
            'moved': article_list_dict['moved'],
            'new_article_title': article_list_dict['new_article_title']
        }
        debug_print("update_data = ", update_data)

        # article_list更新
        # article_detail挿入

        # 新しいDBセッションを生成、取得
        session_id = self.api_db_access.create_session()

        try:
            # トランザクション開始
            self.api_db_access.manage_transaction(session_id, "begin")

            # ２つのテーブルの更新を行う
            response = self.api_db_access.update_article_list(article_list_dict['article_id'], update_data)
            response = self.api_db_access.insert_article_details(new_insert)

            # トランザクションコミット
            self.api_db_access.manage_transaction(session_id, "commit")
        except Exception as e:
            # トランザクションロールバック
            self.api_db_access.manage_transaction(session_id, "rollback")
            raise e
        finally:
            # DBセッションを閉じる
            self.api_db_access.close_session(session_id)    
        return None


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

    # レス番号からページ番号を取得
    def get_page_number_from_res_id(self, res_id):
        # 0以下は1ページ目とする。（未スクレイピング対象であっても、この処理まで来ているということは最低1レスは存在する）
        if res_id < 1:
            res_id = 1
        
        page_number = ((res_id - 1) // RESPONSES_PER_PAGE) * RESPONSES_PER_PAGE + 1
        return page_number

    # ...他のメソッドも同様に...

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
            debug_print(f"page_url [{idx}] = {page_url}", indent=4, short=True)
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


# スクリプトとして実行された場合のエントリポイント
if __name__ == "__main__":
    # コマンドライン引数や設定ファイルからURLを取得する
    # ここは環境に合わせて適切に設定すること
    controller = DetailController("http://api_container:8000")  # 依存するデータベースまたはAPIオブジェクトを渡す
    controller.detail_controller_main()
