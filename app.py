import json
import asyncio
import requests
import logging
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
import argparse
from typing import List
from data_model import MonitorEntry, entry_list_factory
parser = argparse.ArgumentParser()
parser.add_argument("--config", type=str, default="config.json")
args, unknown = parser.parse_known_args()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

RUN_FLAG = True
STARTED_FLAG = False


async def polling_call(monitoring_entry: MonitorEntry, update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RUN_FLAG
    while True:
        if not RUN_FLAG:
            return
        monitoring_entry.pull_data()
        notification = monitoring_entry.notification_str()
        if notification:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=notification)
        await asyncio.sleep(monitoring_entry.interval)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RUN_FLAG
    global STARTED_FLAG
    global entry_list
    if STARTED_FLAG is False:
        STARTED_FLAG = True
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"monitor already started")
        return
    RUN_FLAG = True
    welcome_message = "use /start to start the bot, use /shutdown to shut down. Any other message will trigger a status query\n\n" + "monitoring:\n" + "\n".join([entry.metric_str() for entry in entry_list])
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=welcome_message)
    coroutines = [polling_call(entry, update, context) for entry in entry_list]
    await asyncio.gather(*coroutines)


async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global RUN_FLAG
    if "shutdown" in update.message.text.lower():
        RUN_FLAG = False
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"shutting down")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global entry_list
    status_string = "current status:\n" + "\n".join([entry.status_str() for entry in entry_list])
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=status_string)


if __name__ == '__main__':
    with open(args.config, "r") as fr:
        json_dict = json.load(fr)
    entry_list: List[MonitorEntry] = []
    for json_config_dict in json_dict["configs"]:
        entry_list.extend(entry_list_factory(json_config_dict))
    application = ApplicationBuilder().token(json_dict["bot_token"]).build()
    user_id = int(json_dict["user_id"])
    user_filter = filters.User(user_id=user_id)
    start_handler = CommandHandler("start", start, filters=user_filter, block=False)
    shutdown_handler = CommandHandler("shutdown", shutdown, filters=user_filter)
    status_handler = MessageHandler(filters.TEXT & (~filters.COMMAND) & user_filter, status)

    application.add_handler(start_handler)
    application.add_handler(shutdown_handler)
    application.add_handler(status_handler)
    application.run_polling()
