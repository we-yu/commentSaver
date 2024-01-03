import os, sys
from dotenv import load_dotenv

# .envファイルの絶対パスを設定
env_path = '/app/.env'  # Dockerコンテナ内でのプロジェクトのルートディレクトリ

# utilディレクトリの絶対パスを設定
util_dir = '/app/app/util'  # Dockerコンテナ内でのutilディレクトリのパス

# 環境変数のロード
load_dotenv(env_path)

# パスをシステムに追加
sys.path.append(util_dir)

# 環境変数から設定を読み込む
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
API_URL = "http://api_container:8000"

# print("env_path: ", env_path)
# print("util_dir: ", util_dir)
# print("MYSQL_DATABASE: ", MYSQL_DATABASE)
# print("MYSQL_USER: ", MYSQL_USER)
# print("MYSQL_PASSWORD: ", MYSQL_PASSWORD)