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

    def insert(self, table_class, data):
        new_row = table_class(**data)
        self.session.add(new_row)
        self.session.commit()

    def select(self, table, filter=None):
        if filter is not None:
            rows = self.session.query(table).filter(filter)
        else:
            rows = self.session.query(table).all()
        return rows

    def delete(self, table_name, filter=None):
        table = self.get_table(table_name)
        if filter is not None:
            self.session.execute(table.delete().where(filter))
        else:
            self.session.execute(table.delete())
        self.session.commit()
