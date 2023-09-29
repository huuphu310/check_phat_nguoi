#!/usr/bin/env python
# pylint: disable=unused-argument, import-error
# This program is dedicated to the public domain under the CC0 license.

import logging
import json
import requests
import re
from decouple import config

from telegram import Update, constants
from telegram.ext import Application, CommandHandler, ContextTypes
from ptbcontrib.ptb_jobstores.mongodb import PTBMongoDBJobStore


MONGO_SERVER = config('MONGO_SERVER', default='127.0.0.1')
MONGO_PORT = config('MONGO_PORT', default=27017)
TIME_UPDATE = config('TIME_UPDATE', default=3600*6)
TELEGRAM_TOKEN = config('TELEGRAM_TOKEN', default='')

url = "https://asia-east2-viphamgiaothong2019.cloudfunctions.net/national"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def contains_alpha_and_digit(s):
    return bool(re.search('[a-zA-Z]', s)) and bool(re.search('[0-9]', s))


# Define a few command handlers. These usually take the two arguments update and
# context.
# Best practice would be to replace context with an underscore,
# since context is an unused local variable.
# This being an example and not having context present confusing beginners,
# we decided to have it present as context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    text = f"- Để bot tự động kiểm tra biển số xe phạt nguội hàng ngày hãy sử dụng lệnh: /set Biển_số_xe, VD: /set 30G12345\n\n- Để huỷ theo dõi tự động hãy dùng lệnh /unset Biển_số_xe, VD: /unset 30G12345\n\n- Để kiểm tra các biển đang theo dõi tự động hãy dùng lệnh /checkjob\n\n- Để kiểm tra biển số xe nào đó có đang dính phạt nguội hay không hãy dùng lênh: /check Biển_số_xe, VD: /check 30G12345"
    await update.message.reply_text(text=text, parse_mode=constants.ParseMode.HTML)


async def check_violations(license):
    payload = json.dumps({
        "data": {
            "BienKS": str(license).upper(),
            "Xe": "1"
        }
    })
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        data = json.loads(response.text)

        if data["result"]["isSuccess"]:
            return data["result"]["violations"]
        else:
            return []

    except:
        return []


async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    job = context.job
    license = job.data
    violations = await check_violations(license)
    try:
        for violation in violations:
            if violation["status"] == "Chưa xử phạt":
                text = f"Biển số xe <b>{violation['licenseNumber']}</b> \nGặp lỗi lúc <b>{violation['violationTime']}</b> tại <b>{violation['violationAddress']}</b>.\nLỗi vi phạm: <b>{violation['behavior']}</b>.\nTrạng thái: <b>{violation['status']}</b>.\nSố điện thoại liên hệ: <b>{violation['contactPhone']}</b>,\nĐịa chỉ liên hệ: {violation['contactAddress']}"
                await context.bot.send_message(job.chat_id, text=text, parse_mode=constants.ParseMode.HTML)
        return
    except:
        return


def remove_job_if_exists(chat_id: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        if not check_violations(context.args[0]):
            return False
        else:
            for job in context.job_queue.get_jobs_by_name(str(chat_id)):
                if str(context.args[0]).upper() == str(job.data):
                    job.schedule_removal()
                    return True
            return False
    except:
        return False


async def check_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool | None:
    try:
        chat_id = update.effective_message.chat_id
        n = 0
        for job in context.job_queue.get_jobs_by_name(str(chat_id)):
            n += 1
            license = str(job.data)
            await update.effective_message.reply_text("Biển số xe đang theo dõi: " + license)
        if n == 0:
            await update.effective_message.reply_text("Bạn đang không theo dõi biển số xe nào")
            return
        return True
    except:
        await update.effective_message.reply_text("Bạn đang không theo dõi biển số xe nào")
        return False


async def set_license(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id

    try:
        # args[0] should contain the time for the timer in seconds
        license = context.args[0]
        if not contains_alpha_and_digit(license):
            await update.effective_message.reply_text(
                "Hãy kiểm tra lại biển số xe, hãy nhập biển số xe theo mẫu: /set 30G12345")
            return

        context.job_queue.run_repeating(alarm, 120, chat_id=chat_id, name=str(chat_id), data=license)
        text = "Đã đặt theo dõi tự động biển số xe" + str(license)
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Sử dụng cấu trúc: /set Biển_số_xe")


async def unset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Đã gỡ bỏ theo dõi biển số " + str(
        context.args[0]) if job_removed else "Không tìm thấy thông tin biển số " + str(context.args[0])
    await update.message.reply_text(text)


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    license = context.args[0]
    print(license)
    violations = await check_violations(license)
    try:
        if len(violations) == 0:
            await context.bot.send_message(chat_id, text="Chúc mừng, Biển số " + license + " không có lỗi vi phạm ",
                                           parse_mode=constants.ParseMode.HTML)
            return
        else:
            for violation in violations:
                if violation["status"] == "Chưa xử phạt":
                    text = f"Biển số xe <b>{violation['licenseNumber']}</b> \nGặp lỗi lúc <b>{violation['violationTime']}</b> tại <b>{violation['violationAddress']}</b>.\nLỗi vi phạm: <b>{violation['behavior']}</b>.\nTrạng thái: <b>{violation['status']}</b>.\nSố điện thoại liên hệ: <b>{violation['contactPhone']}</b>,\nĐịa chỉ liên hệ: {violation['contactAddress']}"
                    await context.bot.send_message(chat_id, text=text, parse_mode=constants.ParseMode.HTML)
            return
    except:
        await context.bot.send_message(chat_id, text="Chúc mừng, Biển số " + license + " không có lỗi vi phạm ",
                                       parse_mode=constants.ParseMode.HTML)
        return


def main() -> None:
    """Run bot."""
    DB_URI = "mongodb://"+str(MONGO_SERVER)+":"+str(MONGO_PORT)+"/admin?retryWrites=true&w=majority"
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.job_queue.scheduler.add_jobstore(
        PTBMongoDBJobStore(
            application=application,
            host=DB_URI,
        )
    )

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("set", set_license))
    application.add_handler(CommandHandler("unset", unset))
    application.add_handler(CommandHandler("checkjob", check_job))
    application.add_handler(CommandHandler("check", check))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
