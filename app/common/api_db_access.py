# このファイルは、DBにアクセスするためのAPIを提供する。
import requests
from app.util.debug_tools import debug_print

class API_DB_Access:
    def __init__(self, api_url):
        self.api_url = api_url

    # ArticleList用のAPI関数 -----------------------------------------------------------------------
    def create_article_list(self, article_data):
        debug_print("Inserting into article_list.")

        # バリデーション: 必要なキーが辞書に含まれているか確認
        required_keys = ["article_id", "title", "url", "last_res_id", "moved", "new_article_title"]
        for key in required_keys:
            if key not in article_data:
                print(f"Error: '{key}' is missing from article data.")
                return None

        # データ型とフォーマットのチェック
        if not isinstance(article_data["article_id"], int) or not isinstance(article_data["last_res_id"], int):
            print("Error: 'article_id', 'last_res_id' should be integers.")
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

    def read_article_list_by_id(self, article_id):
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
    
    def read_all_article_list(self):
        print("Fetching all records from article_list.")

        # APIリクエストの送信
        endPointURL = f"{self.api_url}/article_list/all"
        response = requests.get(endPointURL)

        # レスポンスの確認
        if response.status_code == 200:
            api_result = response.json()
            print("Select all from article_list successful, Record count is", len(api_result))
            return api_result
        else:
            print(f"Error during API call: {response.status_code}, {response.text}")
            return None

    def update_article_list(self, article_id, update_data):
        print(f"Updating article_list for article_id={article_id}.")

        # データ型とフォーマットのチェック（必要に応じて）
        if not isinstance(article_id, int):
            print("Error: 'article_id' should be an integer.")
            return None

        # APIリクエストの送信
        endPointURL = f"{self.api_url}/article_list/{article_id}"
        response = requests.put(endPointURL, json=update_data)

        # レスポンスの確認
        if response.status_code == 200:
            print(f"Update article_list successful for article_id={article_id}.")
        else:
            print(f"Error during API call: {response.status_code}, {response.text}")

        return response

    def delete_article_list(self, article_id):
        print(f"Deleting article_list for article_id={article_id}.")

        if not isinstance(article_id, int):
            print("Error: 'article_id' should be an integer.")
            return None

        # APIリクエストの送信
        endPointURL = f"{self.api_url}/article_list/{article_id}"
        response = requests.delete(endPointURL)

        # レスポンスの確認
        if response.status_code == 200:
            print(f"Delete article_list successful for article_id={article_id}.")
        else:
            print(f"Error during API call: {response.status_code}, {response.text}")

        return response

    # ArticleDetail用のAPI関数 ---------------------------------------------------------------------
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
    
    def select_article_details(self, article_id):
        debug_print("Selecting from article_detail.")

        # バリデーション: article_id が整数であることを確認
        if not isinstance(article_id, int):
            debug_print("Error: 'article_id' should be an integer.")
            return None

        # APIリクエストの送信
        # endPointURL = f"{self.api_url}/article_details"
        # response = requests.get(endPointURL, params={"article_id": article_id})

        endPointURL = f"{self.api_url}/article_details/{article_id}"
        response = requests.get(endPointURL)

        # レスポンスの確認
        if response.status_code == 200:
            api_result = response.json()
            debug_print("Select from article_detail successful: Fetched", len(api_result), "records.")
        else:
            debug_print(f"Error during API call: {response.status_code}, {response.text}")

        return response

    # 設定値用のAPI関数 ---------------------------------------------------------------------------
    def read_config_by_type(self, config_type):
        response = requests.get(f"{self.api_url}/config/{config_type}")
        if response.status_code == 200:
            return response.json()
        else:
            debug_print(f"Failed to get config data for {config_type}. Status code: {response.status_code}")
            return None

    def read_website_by_name(self, name):
        response = requests.get(f"{self.api_url}/websites/{name}")
        if response.status_code != 200:
            debug_print("Failed to get website data.")
            return False

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
    def test_api_access(self):
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

    def test_delete_article(self):
        print("API delete article test.")

        # Linuxのarticle_idを指定
        article_id = 473859  # Linux記事のID

        # DELETE処理を実行
        response = self.delete_article_list(article_id)

        # レスポンス結果を確認
        if response and response.status_code == 200:
            print("Delete successful for Linux article.")
        else:
            print("Delete failed for Linux article.")


        return None

    def test_update_article(self):
        print("API update article test.")

        # Linuxのarticle_idを指定
        article_id = 473859  # Linux記事のID

        # 更新データを指定
        update_data = {
            "last_res_id": 200,  # 仮の値
            "moved": True,
            "new_article_title": "474000-article"  # 仮の値
        }

        # UPDATE処理を実行
        response = self.update_article_list(article_id, update_data)

        # レスポンス結果を確認
        if response and response.status_code == 200:
            print("Update successful for Linux article.")
        else:
            print("Update failed for Linux article.")

        return None

    def test_create_article(self):
        print("API insert article test.")

        # 挿入する記事データを指定
        article_data = {
            "article_id": 473859,  # Linux記事のID
            "title": "Linux",
            "url": "https://dic.nicovideo.jp/a/linux",
            "last_res_id": 145,
            "moved": False,
            "new_article_title": None
        }

        # INSERT処理を実行
        response = self.create_article_list(article_data)

        # レスポンス結果を確認
        if response and response.status_code == 200:
            debug_print(f"Insert successful for {article_data['title']} article.")
        else:
            debug_print(f"Insert failed for {article_data['title']} article.")
        
        return None

    def test_create_article_details(self):
        print("API insert article details test.")
        self.api_url = "http://api_container:8000"

        # テスト用の記事詳細データを作成
        article_details_data = [
            {
                "article_id": 20002345,
                "resno": 1,
                "post_name": "テストユーザー1",
                "post_date": "2022-01-01T12:00:00",
                "user_id": "user123",
                "bodytext": "これはテストコメント1です。",
                "page_url": "http://example.com/page1",
                "deleted": False
            },
            {
                "article_id": 4567890,
                "resno": 1,
                "post_name": "テストユーザー2",
                "post_date": "2022-01-02T13:00:00",
                "user_id": "user234",
                "bodytext": "これはテストコメント2です。",
                "page_url": "http://example.com/page2",
                "deleted": False
            },
            {
                "article_id": 4567890,
                "resno": 2,
                "post_name": "テストユーザー3",
                "post_date": "2022-01-03T14:00:00",
                "user_id": "user345",
                "bodytext": "これはテストコメント3です。",
                "page_url": "http://example.com/page3",
                "deleted": False
            },
            {
                "article_id": 5678,
                "resno": 1,
                "post_name": "テストユーザー4",
                "post_date": "2022-01-04T15:00:00",
                "user_id": "user456",
                "bodytext": "これはテストコメント4です。",
                "page_url": "http://example.com/page4",
                "deleted": False
            },
            {
                "article_id": 5678,
                "resno": 2,
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


    def api_read_article_details_sample(self, article_id):
        print(f"API read article details test for article_id={article_id}.")

        # APIリクエストの送信
        response = self.select_article_details(article_id)

        # レスポンス結果を確認
        if response.status_code == 200:
            api_result = response.json()
            print("Read from article_detail successful:", api_result)

            data = response.json()
            # データがリスト形式であることを確認（複数件のデータを取得しているため）
            if isinstance(data, list):
                # 取得した各レコードの詳細を表示
                for item in data:
                    print(f"Article ID: {item.get('article_id', 'N/A')}")
                    print(f"Res No: {item.get('resno', 'N/A')}")
                    print(f"Post Name: {item.get('post_name', 'N/A')}")
                    print(f"Post Date: {item.get('post_date', 'N/A')}")
                    print(f"User ID: {item.get('user_id', 'N/A')}")
                    print(f"Body Text: {item.get('bodytext', 'N/A')}")
                    print(f"Page URL: {item.get('page_url', 'N/A')}")
                    print(f"Deleted: {item.get('deleted', 'N/A')}")
                    print("-" * 30)  # レコード間を区切るための線
            else:
                print("Data format is not a list as expected.")
        else:
            print(f"Error during API call: {response.status_code}, {response.text}")

        return response


    # Trial functions >> ========================================================================
