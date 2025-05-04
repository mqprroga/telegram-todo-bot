import logging
import os
from typing import List
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import TodoItem

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TodoBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.user_states = {}  
       
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.callback_query_handler(func=lambda call: True)(self.button)
        self.bot.message_handler(func=lambda m: True)(self.add_task)
        
        logger.info("Bot initialized")

    def start(self, message: Message, edit_message: bool = False) -> None:
        """Главное меню с кнопками"""
        user = message.from_user if hasattr(message, 'from_user') else message.message.from_user
        chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить задачу", callback_data='add_task')],
            [InlineKeyboardButton("📝 Мои задачи", callback_data='list_tasks')],
            [InlineKeyboardButton("✨ О боте", callback_data='about')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"📝 *Привет, {user.first_name}!*\nЯ твой персональный Todo бот.\n\nВыбери действие:"
        
        if edit_message:
            self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message.message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    def button(self, call: CallbackQuery) -> None:
        """Обработчик inline кнопок"""
        self.bot.answer_callback_query(call.id)
        
        match call.data:
            case 'add_task':
                self._add_task_handler(call)
            case 'list_tasks':
                self.list_tasks(call)
            case 'about':
                self._about_handler(call)
            case 'back':
                self.start(call, edit_message=True)
            case data if data.startswith('delete_task'):
                task_id = int(data.split()[1]) if len(data.split()) > 1 else None
                self.delete_task(call, task_id)
            case data if data.startswith('complete_task'):
                task_id = int(data.split()[1]) if len(data.split()) > 1 else None
                self.complete_task(call, task_id)
            case _:
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="❌ Неизвестная команда"
                )
    
    def _add_task_handler(self, call: CallbackQuery):
        """Обработчик добавления задачи с кнопкой Назад"""
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
    
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✏️ *Напиши задачу, которую хочешь добавить:*\n\nПример: Сделать домашку по математике",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        self.user_states[call.from_user.id] = 'waiting_for_task'
    
    def _about_handler(self, call: CallbackQuery):
        """Информация о боте"""
        text = """
🌟 *Todo Bot*\n
📌 Версия: 1.0
📅 Создан: 2023
🛠 Разработчик: Ваше имя

📝 Этот бот поможет вам организовать свои задачи и никогда ничего не забывать!

🔹 Добавляйте задачи
🔹 Отмечайте выполненные
🔹 Удаляйте ненужные
"""
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    def add_task(self, message: Message) -> None:
        """Добавление новой задачи с возвратом в меню"""
        if message.text.startswith('/') or message.from_user.id not in self.user_states:
            return
        
        task_text = message.text
        user_id = message.from_user.id
    
        db: Session = SessionLocal()
        try:
            new_task = TodoItem(user_id=user_id, task=task_text)
            db.add(new_task)
            db.commit()
       
            self.bot.delete_message(
                chat_id=message.chat.id,
                message_id=message.message_id
            )
       
            keyboard = [[InlineKeyboardButton("В главное меню", callback_data='back')]]
            self.bot.send_message(
                chat_id=message.chat.id,
                text=f"✅ *Задача добавлена!*\n\n`{task_text}`",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            logger.info(f"User {user_id} added task: {task_text}")
        except Exception as e:
            db.rollback()
            self.bot.send_message(
                chat_id=message.chat.id,
                text="❌ Произошла ошибка при добавлении задачи"
            )
            logger.error(f"Error adding task: {e}")
        finally:
            db.close()
            if user_id in self.user_states:
                del self.user_states[user_id]
    
    def list_tasks(self, call: CallbackQuery) -> None:
        """Показать список задач"""
        user_id = call.from_user.id
        db: Session = SessionLocal()
        
        try:
            tasks = db.query(TodoItem).filter(TodoItem.user_id == user_id).order_by(TodoItem.is_completed).all()
            
            if not tasks:
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="📭 У тебя пока нет задач",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='back')]])
                )
                return
            
            message = "📋 *Твой список задач:*\n\n"
            keyboard = []
            
            for task in tasks:
                status = "✅" if task.is_completed else "🟡"
                message += f"{status} `{task.id}. {task.task}`\n"
                
                row = []
                if not task.is_completed:
                    row.append(InlineKeyboardButton(
                        f"✔️ Завершить {task.id}",
                        callback_data=f"complete_task {task.id}"
                    ))
                row.append(InlineKeyboardButton(
                    f"❌ Удалить {task.id}",
                    callback_data=f"delete_task {task.id}"
                ))
                keyboard.append(row)
           
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            logger.info(f"User {user_id} listed tasks")
        except Exception as e:
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ Произошла ошибка при получении задач",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='back')]])
            )
            logger.error(f"Error listing tasks: {e}")
        finally:
            db.close()
    
    def delete_task(self, call: CallbackQuery, task_id: int) -> None:
        """Удаление задачи"""
        user_id = call.from_user.id
        db: Session = SessionLocal()
        
        try:
            task = db.query(TodoItem).filter(
                TodoItem.id == task_id,
                TodoItem.user_id == user_id
            ).first()
            
            if task:
                task_text = task.task
                db.delete(task)
                db.commit()
                self.bot.answer_callback_query(
                    callback_query_id=call.id,
                    text=f"🗑 Задача удалена: {task_text}",
                    show_alert=True
                )
                logger.info(f"User {user_id} deleted task {task_id}")
            else:
                self.bot.answer_callback_query(
                    callback_query_id=call.id,
                    text="⚠️ Задача не найдена",
                    show_alert=True
                )
        except Exception as e:
            db.rollback()
            self.bot.answer_callback_query(
                callback_query_id=call.id,
                text="❌ Ошибка при удалении задачи",
                show_alert=True
            )
            logger.error(f"Error deleting task: {e}")
        finally:
            db.close()
        
        self.list_tasks(call)
    
    def complete_task(self, call: CallbackQuery, task_id: int) -> None:
        """Отметка задачи как выполненной"""
        user_id = call.from_user.id
        db: Session = SessionLocal()
        
        try:
            task = db.query(TodoItem).filter(
                TodoItem.id == task_id,
                TodoItem.user_id == user_id
            ).first()
            
            if task:
                task_text = task.task
                task.is_completed = True
                db.commit()
                self.bot.answer_callback_query(
                    callback_query_id=call.id,
                    text=f"🎉 Задача выполнена: {task_text}",
                    show_alert=True
                )
                logger.info(f"User {user_id} completed task {task_id}")
            else:
                self.bot.answer_callback_query(
                    callback_query_id=call.id,
                    text="⚠️ Задача не найдена",
                    show_alert=True
                )
        except Exception as e:
            db.rollback()
            self.bot.answer_callback_query(
                callback_query_id=call.id,
                text="❌ Ошибка при обновлении задачи",
                show_alert=True
            )
            logger.error(f"Error completing task: {e}")
        finally:
            db.close()
        
        self.list_tasks(call)
    
    def run(self):
        """Запуск бота"""
        logger.info("Starting bot polling...")
        self.bot.infinity_polling()