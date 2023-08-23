from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.orm import sessionmaker

class Database:
    def __init__(self, db_uri):
        self.engine = create_engine(db_uri)

        self.metadata = MetaData()
        self.metadata.bind = self.engine

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_table(self, table_name):
        return Table(table_name, self.metadata, autoload_with=self.engine)

    # Create
    def insert(self, table_class, data):
        new_row = table_class(**data)
        self.session.add(new_row)
        self.session.commit()
    
    # 複数行のデータを一括で挿入する
    def bulk_insert(self, table_class, data_list):
        self.session.bulk_insert_mappings(table_class, data_list)
        self.session.commit()

    # Read
    def select(self, table, filter=None):
        if filter is not None:
            rows = self.session.query(table).filter(filter)
        else:
            rows = self.session.query(table).all()
        return rows

    # Update
    def update(self, table_class, filter, data):
        row = self.session.query(table_class).filter(filter).first()
        if row:
            for key, value in data.items():
                setattr(row, key, value)
            self.session.commit()

    # Delete
    def delete(self, table_name, filter=None):
        table = self.get_table(table_name)
        if filter is not None:
            self.session.execute(table.delete().where(filter))
        else:
            self.session.execute(table.delete())
        self.session.commit()

    # 既存のキーのセットを取得する
    def get_existing_keys(self, table_class, primary_keys):
        """
        対象のテーブルに存在しているデータのキー一覧を取得する関数。
        
        Parameters:
        - table_class: SQLAlchemyのテーブルクラス
        - primary_keys: プライマリキー（または複合キー）のカラム名のリスト
        
        Returns:
        - existing_keys_set: 既存のキーのセット

        Examples:
        existing_keys_set = db.get_existing_keys(ArticleDetail, ['article_id', 'resno'])
        """
        query = self.session.query(*[getattr(table_class, key) for key in primary_keys])
        existing_keys = query.all()
        existing_keys_set = set(existing_keys)
        return existing_keys_set
