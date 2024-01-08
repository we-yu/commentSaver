import os, inspect

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.normpath(os.path.join(CURRENT_FILE_DIR, '../config/conf.txt'))

def get_debug_value_from_config(file_path=CONFIG_PATH):
    with open(file_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if "DEBUG" in line:
                return line.split('=')[1].strip().lower() == 'true'
    return False

DEBUG = get_debug_value_from_config()

def debug_print(*args, indent=0, short=False, **kwargs):
    if DEBUG:
        # インデントをスペースで作成
        indent_str = ' ' * indent

        # 短縮形式でない場合のみファイル名、関数名、行番号を含める
        if not short:
            # 実行中のコードのスタックフレームを取得
            stack = inspect.stack()
            # 呼び出し元の情報を取得（0は現在の関数、1は呼び出し元）
            the_caller = stack[1]
            # ファイル名、関数名、行番号を取得
            filename = os.path.basename(the_caller.filename)
            lineno = the_caller.lineno
            funcname = the_caller.function
            # メッセージの前にファイル名、関数名、行番号を付加
            print(f"{indent_str}{filename}: {funcname}: {lineno} ▶", *args, **kwargs)
        else:
            # 短縮形式の場合は、インデントとメッセージのみを出力
            print(f"{indent_str}", *args, **kwargs)

import requests
def debug_apicall():
    # apiのホスト名とポート番号を指定します
    url = "http://api:8000/article_list"

    # オプショナル: クエリパラメータを指定する場合
    params = {'article_id': 430509}

    # GETリクエストを送信
    response = requests.get(url, params=params)

    # レスポンスを出力
    print(response.json())

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'debug_apicall':
        debug_apicall()
