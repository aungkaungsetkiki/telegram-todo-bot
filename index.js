const { Telegraf } = require('telegraf');
const { query } = require('./db');
require('dotenv').config();

const bot = new Telegraf(process.env.BOT_TOKEN);

// Command handlers
bot.start((ctx) => ctx.reply('Welcome to your To-Do List Bot! Use /add, /list, /complete, or /delete.'));

bot.command('add', async (ctx) => {
  const taskText = ctx.message.text.replace('/add', '').trim();
  
  if (!taskText) {
    return ctx.reply('Please provide a task after /add command.');
  }

  try {
    await query(
      'INSERT INTO tasks (user_id, task) VALUES ($1, $2)',
      [ctx.from.id, taskText]
    );
    ctx.reply(`Task added: ${taskText}`);
  } catch (err) {
    console.error(err);
    ctx.reply('Error adding task.');
  }
});

bot.command('list', async (ctx) => {
  try {
    const result = await query(
      'SELECT id, task, completed FROM tasks WHERE user_id = $1 ORDER BY created_at',
      [ctx.from.id]
    );
    
    if (result.rows.length === 0) {
      return ctx.reply('Your to-do list is empty.');
    }
    
    const tasks = result.rows.map((task, index) => 
      `${index + 1}. ${task.completed ? '✅' : '◻️'} ${task.task} (ID: ${task.id})`
    ).join('\n');
    
    ctx.reply(`Your To-Do List:\n${tasks}`);
  } catch (err) {
    console.error(err);
    ctx.reply('Error retrieving your to-do list.');
  }
});

bot.command('complete', async (ctx) => {
  const taskId = ctx.message.text.replace('/complete', '').trim();
  
  if (!taskId) {
    return ctx.reply('Please provide a task ID after /complete command.');
  }

  try {
    const result = await query(
      'UPDATE tasks SET completed = TRUE WHERE id = $1 AND user_id = $2 RETURNING task',
      [taskId, ctx.from.id]
    );
    
    if (result.rowCount === 0) {
      return ctx.reply('Task not found or already completed.');
    }
    
    ctx.reply(`Task marked as completed: ${result.rows[0].task}`);
  } catch (err) {
    console.error(err);
    ctx.reply('Error completing task.');
  }
});

bot.command('delete', async (ctx) => {
  const taskId = ctx.message.text.replace('/delete', '').trim();
  
  if (!taskId) {
    return ctx.reply('Please provide a task ID after /delete command.');
  }

  try {
    const result = await query(
      'DELETE FROM tasks WHERE id = $1 AND user_id = $2 RETURNING task',
      [taskId, ctx.from.id]
    );
    
    if (result.rowCount === 0) {
      return ctx.reply('Task not found.');
    }
    
    ctx.reply(`Task deleted: ${result.rows[0].task}`);
  } catch (err) {
    console.error(err);
    ctx.reply('Error deleting task.');
  }
});

// Error handling
bot.catch((err, ctx) => {
  console.error(`Error for ${ctx.updateType}:`, err);
  ctx.reply('An error occurred. Please try again.');
});

// Start the bot
bot.launch().then(() => {
  console.log('Bot is running');
});

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
