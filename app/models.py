from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Title(Base):
    __tablename__ = 'titles'

    id = Column(Integer, primary_key=True)
    title = Column(String)

class Config(Base):
    __tablename__ = 'scrape_config'

    id = Column(Integer, primary_key=True)
    config_type = Column(String)
    value = Column(String)

class ArticleList(Base):
    __tablename__ = 'article_list'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer)
    title = Column(String(255), nullable=False)
    url = Column(String(255), nullable=False)
    last_res_id = Column(Integer)
    moved = Column(Boolean)
    new_id = Column(Integer)

class ArticleDetail(Base):
    __tablename__ = 'article_detail'

    article_id = Column(Integer, primary_key=True)
    resno = Column(Integer, primary_key=True)
    post_name = Column(String(255))
    post_date = Column(DateTime)
    user_id = Column(String(255))
    bodytext = Column(Text)
    page_url = Column(String(255))
    deleted = Column(Boolean)

class Website(Base):
    __tablename__ = 'websites'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)
    sub_tag1 = Column(String)
    sub_tag2 = Column(String)
    sub_tag3 = Column(String)

    def __repr__(self):
            return f"Website(id={self.id}, name={self.name}, url={self.url}, sub_tag1={self.sub_tag1}, sub_tag2={self.sub_tag2}, sub_tag3={self.sub_tag3})"