# このファイルは、DBにアクセスするためのAPIを提供する。
import requests
from debug_tools import debug_print

    

class API_DB_Access:
    def __init__(self, api_url):
        self.api_url = api_url

    def insert_article_list(self, article_data):
        print("Inserting into article_list.")

        # バリデーション: 必要なキーが辞書に含まれているか確認
        required_keys = ["article_id", "title", "url", "last_res_id", "moved", "new_id"]
        for key in required_keys:
            if key not in article_data:
                print(f"Error: '{key}' is missing from article data.")
                return None

        # データ型とフォーマットのチェック
        if not isinstance(article_data["article_id"], int) or not isinstance(article_data["last_res_id"], int) or not isinstance(article_data["new_id"], int):
            print("Error: 'article_id', 'last_res_id', 'new_id' should be integers.")
            return None
        if not isinstance(article_data["moved"], bool):
            print("Error: 'moved' should be a boolean value.")
            return None
        if not article_data["url"].startswith("http://") and not article_data["url"].startswith("https://"):
            print("Error: 'url' is not in valid format.")
            return None

        # APIリクエストの送信
        endPointURL = f"{self.api_url}/article_list"
        response = requests.post(endPointURL, json=article_data)

        # レスポンスの確認
        if response.status_code == 200:
            print("Insert into article_list successful.")
        else:
            print(f"Error during API call: {response.status_code}, {response.text}")

        return response

    def select_article_list(self, article_id):
        print("Selecting from article_list.")

        # バリデーション: article_id が整数であることを確認
        if not isinstance(article_id, int):
            print("Error: 'article_id' should be an integer.")
            return None

        # APIリクエストの送信
        endPointURL = f"{self.api_url}/article_list"
        response = requests.get(endPointURL, params={"article_id": article_id})

        # レスポンスの確認
        if response.status_code == 200:
            api_result = response.json()
            print("Select from article_list successful:", api_result)
        else:
            print(f"Error during API call: {response.status_code}, {response.text}")

        return response

    def insert_article_details(self, details_data):
        print("Inserting into article_detail.")

        # バリデーション: details_data がリスト形式であることを確認
        if not isinstance(details_data, list):
            print("Error: 'details_data' should be a list.")
            return None

        # 各レコードのバリデーション
        for record in details_data:
            required_keys = ["article_id", "resno", "post_name", "post_date", "user_id", "bodytext", "page_url", "deleted"]
            for key in required_keys:
                if key not in record:
                    print(f"Error: '{key}' is missing from detail record.")
                    return None

        # APIリクエストの送信
        endPointURL = f"{self.api_url}/article_details"
        response = requests.post(endPointURL, json=details_data)

        # レスポンスの確認
        if response.status_code == 200:
            print("Insert into article_detail successful.")
        else:
            print(f"Error during API call: {response.status_code}, {response.text}")

        return response

    # << Trial functions ========================================================================
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


    # ScraperコンテナからAPIコンテナのAPI呼び出しテスト
    def api_access_sample(self):
        print("API access test.")

        article_id = 430509
        response = requests.get(f"{self.api_url}/article_list", params={"article_id": article_id})
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

        endPointURL = f"{self.api_url}/article_list/{article_id}"

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

        endPointURL = f"{self.api_url}/article_list/{article_id}"

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

        endPointURL = f"{self.api_url}/article_list"

        debug_print("endPointURL = ", endPointURL)
        
        # POSTリクエストを送信
        response = requests.post(endPointURL, json=article_data)

        # レスポンス結果を確認
        if response.status_code == 200:
            api_result = response.json()
            print("Insert successful:", api_result)
        else:
            print("Error:", response.status_code, response.text)
        
        return response

    def api_insert_article_details_sample(self):
        print("API insert article details test.")
        self.api_url = "http://api_container:8000"

        # テスト用の記事詳細データを作成
        article_details_data = [
            {
                "article_id": 12436,
                "resno": 1,
                "post_name": "テストユーザー1",
                "post_date": "2022-01-01T12:00:00",
                "user_id": "user123",
                "bodytext": "これはテストコメント1です。",
                "page_url": "http://example.com/page1",
                "deleted": False
            },
            {
                "article_id": 12436,
                "resno": 2,
                "post_name": "テストユーザー2",
                "post_date": "2022-01-02T13:00:00",
                "user_id": "user234",
                "bodytext": "これはテストコメント2です。",
                "page_url": "http://example.com/page2",
                "deleted": False
            },
            {
                "article_id": 12436,
                "resno": 3,
                "post_name": "テストユーザー3",
                "post_date": "2022-01-03T14:00:00",
                "user_id": "user345",
                "bodytext": "これはテストコメント3です。",
                "page_url": "http://example.com/page3",
                "deleted": False
            },
            {
                "article_id": 12436,
                "resno": 4,
                "post_name": "テストユーザー4",
                "post_date": "2022-01-04T15:00:00",
                "user_id": "user456",
                "bodytext": "これはテストコメント4です。",
                "page_url": "http://example.com/page4",
                "deleted": False
            },
            {
                "article_id": 12436,
                "resno": 5,
                "post_name": "テストユーザー5",
                "post_date": "2022-01-05T16:00:00",
                "user_id": "user567",
                "bodytext": "これはテストコメント5です。",
                "page_url": "http://example.com/page5",
                "deleted": False
            }
            # 他のレコードも同様に追加
        ]

        endPointURL = f"{self.api_url}/article_details"

        # POSTリクエストを送信
        response = requests.post(endPointURL, json=article_details_data)

        # レスポンス結果を確認
        if response.status_code == 200:
            print("Insert successful")
        else:
            print("Error:", response.status_code, response.text)

        return None

    # Trial functions >> ========================================================================
