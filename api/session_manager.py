from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from contextlib import contextmanager

class SessionManager:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.sessions = {}

    def create_session(self):
        db_session = self.SessionLocal()
        session_id = id(db_session)
        self.sessions[session_id] = db_session
        return session_id

    def close_session(self, session_id):
        session = self.get_session_by_id(session_id)
        if session:
            session.close()
            del self.sessions[session_id]

    def begin_transaction(self, session_id):
        session = self.get_session_by_id(session_id)
        session.begin()

    def commit_transaction(self, session_id):
        session = self.get_session_by_id(session_id)
        session.commit()

    def rollback_transaction(self, session_id):
        session = self.get_session_by_id(session_id)
        session.rollback()

    def get_session_by_id(self, session_id):
        return self.sessions.get(session_id, None)

    @contextmanager
    def session(self):
        # セッションIDではなくセッションオブジェクトを取得
        db_session = self.SessionLocal()
        try:
            yield db_session
            db_session.commit()
        except:
            db_session.rollback()
            raise
        finally:
            db_session.close()
