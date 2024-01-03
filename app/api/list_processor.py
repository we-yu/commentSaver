import sys
from urllib.parse import quote
import urllib.request
import ssl
from bs4 import BeautifulSoup

# Local
from app.common.api_db_access import API_DB_Access
import app.common.settings

from debug_tools import debug_print
from error_handler import ErrorHandler, PROGRAM_EXIT, PROGRAM_CONTINUE

NICOPEDY_DOMAIN = "dic.nicovideo.jp"
NICOPEDY_PATH_TANGO = "a"

class ListProcessor:
    def __init__(self, api_url):
        self.api_db_access = API_DB_Access(api_url)

    def list_processor_main(self, article_url):

        # 日本語記事名に対応するため、URLエンコードを行う
        debug_print(f"Func: list_processor_main(), arg = {article_url}")
        encoded_url = quote(article_url, safe='/:?=&')
        debug_print("Scraping target URL = ", article_url, "encoded_url = ", encoded_url)
        url = encoded_url

        # バリデーションチェック

        # 対象がニコ百記事として適正なURLかチェック
        if self.is_valid_url(url) == False:
            debug_print("Invalid URL.")
            return False
        debug_print("Valid URL.")

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
        # 記事IDが取得できなかった場合は終了
        if article_id == None:
            debug_print("Failed to get article ID.")
            exit(1)

        article_id = int(article_id)

        debug_print("article_id = ", article_id)

        # 記事が既にスクレイピング済みかチェック。スクレイピング済みであれば対象レコードを取得。
        fetched_record = self.is_already_scraped(article_id)

        # 対象記事が未取得の場合
        if fetched_record is None:
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
        # 対象記事が取得済みの場合は終了
        else:
            return None

        # 記事一覧テーブルにレコードを追加
        debug_print("Currently data of article_list_dict = ", article_list_dict)
        # self.api_db_access.create_article_list(article_list_dict)

        # 既存記事が指定された場合、特にデータの更新は行わない。（定期処理でlistとdetail両方更新する）

        return None

    # 対象が適正なニコ記事かどうかチェック.
    def is_valid_url(self, targetArtURL):
        debug_print(f"Func: is_valid_url(), arg = {targetArtURL}")

        response = self.api_db_access.read_website_by_name("Niconico")
        if response.status_code == 200:
            website_data = response.json()
            nico_url = website_data['url'].lower()
            tag1 = website_data['sub_tag1'].lower()
            is_Nicopedi_URL = targetArtURL.startswith(nico_url + tag1 + "/")
            return is_Nicopedi_URL
        else:
            return False

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


    def call_scraping(self, article_title):
        debug_print("Func: call_scraping()")

        # URLを生成
        article_url = f"https://{NICOPEDY_DOMAIN}/{NICOPEDY_PATH_TANGO}/{article_title}"

        # scraper.test_api_access()

        # self.api_db_access.test_create_article()

        # scraper.api_db_access.test_update_article()
        # scraper.api_db_access.test_delete_article()

        # scraper.api_db_access.test_create_article_details()
        # response = scraper.api_db_access.api_read_article_details_sample(4567890)

        self.list_processor_main(article_url)

# スクリプトとして実行された場合のエントリポイント
if __name__ == "__main__":
    if len(sys.argv) > 1:
        article_title = sys.argv[1]
        processor = ListProcessor("http://api_container:8000")
        processor.call_scraping(article_title)
    else:
        print("No article title provided. Exiting program.")