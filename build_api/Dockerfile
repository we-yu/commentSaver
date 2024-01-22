# オフィシャルのPythonイメージをベースにするわ
FROM python:3.8-slim

# 作業ディレクトリを設定する
WORKDIR /app

# 依存関係をインストールするためのファイルをコピー
COPY ./build_api/requirements.txt .

# RUN apt-get update && apt-get install -y curl

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# APIのソースコードをコピー
COPY ./api /app

# ポートを公開するわ
EXPOSE 8000

# Uvicornを使ってアプリを実行
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
