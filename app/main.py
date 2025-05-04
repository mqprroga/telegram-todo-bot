
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, database
from .models import TodoItem
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация базы данных
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Telegram Todo Bot API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TodoItemCreate(BaseModel):
    task: str
    user_id: int

class TodoItemResponse(BaseModel):
    id: int
    user_id: int
    task: str
    is_completed: bool
    
    class Config:
        orm_mode = True

@app.post("/tasks/", response_model=TodoItemResponse)
def create_task(task: TodoItemCreate, db: Session = Depends(database.get_db)):
    """Создание новой задачи через API"""
    logger.info(f"Creating task for user {task.user_id}")
    db_task = models.TodoItem(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/tasks/{user_id}", response_model=list[TodoItemResponse])
def read_tasks(user_id: int, db: Session = Depends(database.get_db)):
    """Получение списка задач пользователя через API"""
    logger.info(f"Getting tasks for user {user_id}")
    tasks = db.query(models.TodoItem).filter(models.TodoItem.user_id == user_id).all()
    return tasks

@app.put("/tasks/{task_id}/complete", response_model=TodoItemResponse)
def complete_task(task_id: int, db: Session = Depends(database.get_db)):
    """Отметка задачи как выполненной через API"""
    logger.info(f"Completing task {task_id}")
    task = db.query(models.TodoItem).filter(models.TodoItem.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_completed = True
    db.commit()
    db.refresh(task)
    return task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(database.get_db)):
    """Удаление задачи через API"""
    logger.info(f"Deleting task {task_id}")
    task = db.query(models.TodoItem).filter(models.TodoItem.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}

@app.get("/")
def read_root():
    """Корневой endpoint для проверки работы API"""
    return {"message": "Telegram Todo Bot API is running"}