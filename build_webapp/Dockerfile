# Node.jsの公式イメージをベースにする
FROM node:14

# 作業ディレクトリを設定
WORKDIR /webapp

# 依存関係をインストールするためのファイルをコピー
COPY ./webapp/my-app/package.json ./
COPY ./webapp/my-app/package-lock.json ./

# 依存関係をインストール
RUN npm install

# アプリケーションのソースコードをコピー
COPY ./webapp/my-app/ .

# ポート3000を公開（Reactのデフォルトポート）
EXPOSE 3000

# アプリケーションを起動
CMD ["npm", "start"]

## 以下は初期化時。
# - 以下の設定でコンテナ起動。
# - コンテナにログインし、Reactアプリを初期化する
#    - docker exec -it webapp_container /bin/bash
#    - npx create-react-app my-app
# - 必要な.jsonやパッケージがそろっている。

# # Node.jsの公式イメージをベースにする
# FROM node:14

# # 作業ディレクトリを設定
# WORKDIR /webapp

# # ポート3000を公開（Reactのデフォルトポート）
# EXPOSE 3000

# # コンテナが起動した際に実行されるコマンド
# # CMD ["npm", "start"]
# CMD ["tail", "-f", "/dev/null"]
