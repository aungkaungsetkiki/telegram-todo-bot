import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from database import get_connection
from dotenv import load_dotenv

load_dotenv()

# Conversation states
ADD_TASK, ADD_DESCRIPTION, ADD_DUE_DATE = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    
    # Register user
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (user_id, username, first_name, last_name) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (user_id) DO NOTHING",
                (user.id, user.username, user.first_name, user.last_name)
            )
        conn.commit()
    except Exception as e:
        print(f"Error registering user: {e}")
    finally:
        conn.close()
    
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        "I'm your Todo Bot. Commands:\n"
        "/add - Add task\n"
        "/list - Show tasks\n"
        "/complete <id> - Complete task\n"
        "/delete <id> - Delete task"
    )

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding task"""
    await update.message.reply_text("📝 Enter task title:")
    return ADD_TASK

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive task title"""
    context.user_data['title'] = update.message.text
    await update.message.reply_text(
        "📄 Enter description (or /skip):"
    )
    return ADD_DESCRIPTION

async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip description"""
    context.user_data['description'] = None
    await update.message.reply_text(
        "📅 Enter due date (YYYY-MM-DD or /skip):"
    )
    return ADD_DUE_DATE

async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive description"""
    context.user_data['description'] = update.message.text
    await update.message.reply_text(
        "📅 Enter due date (YYYY-MM-DD or /skip):"
    )
    return ADD_DUE_DATE

async def receive_due_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive due date (date only)"""
    due_date = update.message.text
    context.user_data['due_date'] = due_date if due_date.lower() != '/skip' else None
    
    # Save to database
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (user_id, title, description, due_date) "
                "VALUES (%s, %s, %s, %s::date)",
                (
                    update.effective_user.id,
                    context.user_data['title'],
                    context.user_data['description'],
                    context.user_data['due_date']
                )
            )
        conn.commit()
        await update.message.reply_text("✅ Task added!")
    except Exception as e:
        print(f"Error adding task: {e}")
        await update.message.reply_text("❌ Failed. Use YYYY-MM-DD format.")
    finally:
        conn.close()
    
    return ConversationHandler.END

async def skip_due_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip due date"""
    # Save to database
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (user_id, title, description) "
                "VALUES (%s, %s, %s)",
                (
                    update.effective_user.id,
                    context.user_data['title'],
                    context.user_data['description']
                )
            )
        conn.commit()
        await update.message.reply_text("✅ Task added!")
    except Exception as e:
        print(f"Error adding task: {e}")
        await update.message.reply_text("❌ Failed to add task.")
    finally:
        conn.close()
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel operation"""
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all tasks"""
    user_id = update.effective_user.id
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT task_id, title, description, due_date, completed "
                "FROM tasks WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            tasks = cur.fetchall()
            
            if not tasks:
                await update.message.reply_text("You have no tasks!")
                return
            
            message = "📋 Your Tasks:\n\n"
            for task in tasks:
                task_id, title, desc, due_date, completed = task
                status = "✅" if completed else "🟡"
                message += f"{status} <b>{title}</b> (ID: {task_id})\n"
                if desc:
                    message += f"   - {desc}\n"
                if due_date:
                    message += f"   - Due: {due_date}\n"
                message += "\n"
            
            await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        print(f"Error listing tasks: {e}")
        await update.message.reply_text("❌ Failed to load tasks.")
    finally:
        conn.close()

async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark task as complete"""
    if not context.args:
        await update.message.reply_text("Usage: /complete <task_id>")
        return
    
    task_id = context.args[0]
    user_id = update.effective_user.id
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verify task exists
            cur.execute(
                "SELECT 1 FROM tasks WHERE task_id = %s AND user_id = %s",
                (task_id, user_id)
            )
            if not cur.fetchone():
                await update.message.reply_text("Task not found!")
                return
            
            # Update task
            cur.execute(
                "UPDATE tasks SET completed = TRUE, updated_at = CURRENT_DATE "
                "WHERE task_id = %s",
                (task_id,)
            )
            conn.commit()
            await update.message.reply_text(f"✅ Task {task_id} completed!")
    except Exception as e:
        print(f"Error completing task: {e}")
        await update.message.reply_text("❌ Failed to complete task.")
    finally:
        conn.close()

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a task"""
    if not context.args:
        await update.message.reply_text("Usage: /delete <task_id>")
        return
    
    task_id = context.args[0]
    user_id = update.effective_user.id
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verify task exists
            cur.execute(
                "SELECT 1 FROM tasks WHERE task_id = %s AND user_id = %s",
                (task_id, user_id)
            )
            if not cur.fetchone():
                await update.message.reply_text("Task not found!")
                return
            
            # Delete task
            cur.execute(
                "DELETE FROM tasks WHERE task_id = %s",
                (task_id,)
            )
            conn.commit()
            await update.message.reply_text(f"🗑️ Task {task_id} deleted!")
    except Exception as e:
        print(f"Error deleting task: {e}")
        await update.message.reply_text("❌ Failed to delete task.")
    finally:
        conn.close()

def main():
    """Start the bot"""
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_TOKEN not set")
    
    app = Application.builder().token(token).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_task)],
        states={
            ADD_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
            ADD_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
                CommandHandler('skip', skip_description)
            ],
            ADD_DUE_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_due_date),
                CommandHandler('skip', skip_due_date)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Add handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('list', list_tasks))
    app.add_handler(CommandHandler('complete', complete_task))
    app.add_handler(CommandHandler('delete', delete_task))
    
    # Start bot
    app.run_polling()

if __name__ == '__main__':
    main()
