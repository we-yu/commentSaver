import sys
import ssl
import urllib.request
from bs4 import BeautifulSoup

from error_handler import ErrorHandler, PROGRAM_EXIT, PROGRAM_CONTINUE
from debug_tools import debug_print

# app/util/common_utils.py
class CommonUtils:

    @staticmethod
    def sample_common_utils(value):
        print("Called CommonUtils, value is ->", value)
        return value * 2

    @staticmethod
    def is_valid_url(url):
        # URLのバリデーションロジック
        pass

    # 対象URLからスクレイピングデータの取得、ページが存在しない場合はメッセージ表示して終了
    @staticmethod
    def scrape_article_top(url):
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
    @staticmethod
    def check_redirect(soup):
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
