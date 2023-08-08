import requests
from bs4 import BeautifulSoup
import pymysql
from pprint import pprint
import sys

# ユーザ記事URLであることをマッチする確認用
NICOPEDI_URL_HEAD_A = "https://dic.nicovideo.jp/a/"

def validate_website_name():
    return None

def scrape_data(url):
    return None

def save_data_to_db(data):
    return None

if __name__ == "__main__":
    args = sys.argv
    data = scrape_data("http://example.com")
    print("data = ", data)
    print(type(data))
    save_data_to_db(data)

#aaaaaaaaaaaaaaaaaaa