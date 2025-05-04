from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TodoItem(Base):
    __tablename__ = 'todo_items'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    task = Column(String(255), nullable=False)
    is_completed = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<TodoItem(user_id={self.user_id}, task='{self.task}', is_completed={self.is_completed})>"