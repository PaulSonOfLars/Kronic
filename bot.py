#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
import logging
import os
import subprocess
import sys
import time
from uuid import uuid4

from telegram import InlineQueryResultArticle, ChatAction, InputTextMessageContent, Update
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, run_async

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('bot.ini')

updater = Updater(token=config['KEYS']['bot_api'])
path = config['PATH']['path']
sudo_users = [138554855, 92027269]
dispatcher = updater.dispatcher


@run_async
def build(bot, update):
    if is_authorized(update):
        bot.sendChatAction(chat_id=update.message.chat_id,
                           action=ChatAction.TYPING)
        os.chdir(path)
        bot.sendMessage(update.message.chat_id, "Building!")
        os.system('cd ~/src && bash aosip.sh %s %s' % (update.message.chat_id, update.message.text))
        bot.sendMessage(update.message.chat_id, "Build is done, bot is usable again!")
    else:
        send_not_authorized_message(bot, update)


@run_async
def sync(bot, update):
    if is_authorized(update):
        bot.sendMessage(update.message.chat_id, text="Starting repo sync")
        os.system("bash ~/Kronicbot/sync.sh %s" % update.message.chat_id)
    else:
        send_not_authorized_message(bot, update)


@run_async
def pick(bot, update):
    if is_authorized(update):
        bot.sendMessage(update.message.chat_id, text="Picking stuff")
        os.system("bash ~/Kronicbot/pick.sh %s %s" % (update.message.chat_id, update.message.text))
    else:
        send_not_authorized_message(bot, update)


@run_async
def clean(bot, update):
    if is_authorized(update):
        bot.sendMessage(update.message.chat_id, text="Cleaning")
        os.system("bash ~/Kronicbot/clean.sh %s" % update.message.chat_id)
    else:
        send_not_authorized_message(bot, update)


# Not async because used by pull
def restart(bot, update):
    if is_authorized(update):
        bot.sendMessage(update.message.chat_id, "Bot is restarting...")
        time.sleep(0.2)
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        send_not_authorized_message(bot, update)


@run_async
def leave(bot, update):
    if is_authorized(update):
        bot.sendChatAction(update.message.chat_id, ChatAction.TYPING)
        bot.sendMessage(update.message.chat_id, "Goodbye!")
        bot.leaveChat(update.message.chat_id)
    else:
        send_not_authorized_message(bot, update)


@run_async
def inlinequery(bot, update):
    query = update.inline_query.query
    o = execute(query, update, direct=False)
    results = list()

    results.append(InlineQueryResultArticle(id=uuid4(),
                                            title=query,
                                            description=o,
                                            input_message_content=InputTextMessageContent(
                                                '*{0}*\n\n{1}'.format(query, o),
                                                parse_mode="Markdown")))

    bot.answerInlineQuery(update.inline_query.id, results=results, cache_time=10)


def send_not_authorized_message(bot, update):
    bot.sendChatAction(chat_id=update.message.chat_id,
                       action=ChatAction.TYPING)
    bot.sendMessage(chat_id=update.message.chat_id, reply_to_message_id=update.message.message_id,
                    text="You aren't authorized for this lulz!")


@run_async
def help(bot, update):
    bot.sendChatAction(update.message.chat_id, ChatAction.TYPING)
    bot.sendMessage(update.message.chat_id, reply_to_message_id=update.message.message_id,
                    text="I've sent you help via PM @" + update.message.from_user.username + ".")
    bot.sendMessage(update.message.from_user.id,
                    text="Here is some help for you.\n/build,\n/upload,\n/restart,\n/leave, and\n/help for this menu.")


def is_authorized(update):
    return update.message.from_user.id in sudo_users


@run_async
def pull(bot, update):
    if is_authorized(update):
        bot.sendChatAction(update.message.chat_id, ChatAction.TYPING)
        bot.sendMessage(update.message.chat_id, reply_to_message_id=update.message.message_id,
                        text="Fetching remote repo")
        subprocess.call(['git', 'fetch', 'origin', 'master', '--force'])
        bot.sendMessage(update.message.chat_id, reply_to_message_id=update.message.message_id,
                        text="Resetting to latest commit")
        subprocess.call(['git', 'reset', '--hard', 'origin/master'])
        restart(bot, update)
    else:
        send_not_authorized_message(bot, update)


@run_async
def push(bot, update):
    if is_authorized(update):
        subprocess.call(['git', 'push', 'origin', 'master', '--force'])
        bot.sendMessage(update.message.chat_id, text="K pushed")
    else:
        send_not_authorized_message(bot, update)


@run_async
def id(bot, update):
    chatid = str(update.message.chat_id)
    try:
        username = str(update.message.reply_to_message.from_user.username)
        userid = str(update.message.reply_to_message.from_user.id)
        bot.sendChatAction(update.message.chat_id, ChatAction.TYPING)
        time.sleep(1)
        bot.sendMessage(update.message.chat_id, text="ID of @" + username + " is " + userid,
                        reply_to_message_id=update.message.reply_to_message.message_id)
    except AttributeError:
        bot.sendMessage(update.message.chat_id, text="ID of this group is " + chatid,
                        reply_to_message_id=update.message.message_id)


def get_admin_ids(bot, chat_id):
    return [admin.user.id for admin in bot.getChatAdministrators(chat_id)]


@run_async
def kick(bot, update):
    chat = update.message.chat_id
    try:
        sender = update.message.from_user.id
        quoted = update.message.reply_to_message.from_user.id
        if sender in get_admin_ids(bot, chat) and quoted not in get_admin_ids(bot, chat):
            bot.kickChatMember(chat, quoted)
            bot.unbanChatMember(chat, quoted)
            update.message.reply_text(update.message.reply_to_message.from_user.first_name + " kicked!")
        else:
            update.message.reply_text("Meh, either you're not an admin or the quoted user is one!")
    except AttributeError:
        update.message.reply_text(reply_to_message_id=update.message.message_id, text="Please quote a user to kick!")


@run_async
def ban(bot, update):
    chat = update.message.chat_id
    try:
        sender = update.message.from_user.id
        quoted = update.message.reply_to_message.from_user.id
        if sender in get_admin_ids(bot, chat) and quoted not in get_admin_ids(bot, chat):
            bot.kickChatMember(chat, quoted)
            update.message.reply_text(update.message.reply_to_message.from_user.first_name + " cannot join back now!")
        else:
            update.message.reply_text("Meh, either you're not an admin or the quoted user is one!")
    except AttributeError:
        update.message.reply_text(reply_to_message_id=update.message.message_id, text="Please quote a user to ban!")


@run_async
def unban(bot, update):
    chat = update.message.chat_id
    try:
        sender = update.message.from_user.id
        quoted = update.message.reply_to_message.from_user.id
        if sender in get_admin_ids(bot, chat) and quoted not in get_admin_ids(bot, chat):
            bot.unbanChatMember(chat, quoted)
            update.message.reply_text(update.message.reply_to_message.from_user.first_name + " can join this chat now!")
        else:
            update.message.reply_text("Meh, either you're not an admin or the quoted user is one!")
    except AttributeError:
        update.message.reply_text(reply_to_message_id=update.message.message_id, text="Please quote a user to unban!")


@run_async
def mute(bot, update):
    chat = update.message.chat_id
    try:
        sender = update.message.from_user.id
        quoted = update.message.reply_to_message.from_user.id
        if sender in get_admin_ids(bot, chat) and quoted not in get_admin_ids(bot, chat):
            bot.restrictChatMember(chat, quoted, can_send_messages=False, can_send_media_messages=False,
                                   can_send_other_messages=False, can_add_web_page_previews=False)
            update.message.reply_text(update.message.reply_to_message.from_user.first_name + " cannot speak now!")
        else:
            update.message.reply_text("Meh, either you're not an admin or the quoted user is one!")
    except AttributeError:
        update.message.reply_text(reply_to_message_id=update.message.message_id, text="Please quote a user to mute!")


@run_async
def unmute(bot, update):
    chat = update.message.chat_id
    try:
        sender = update.message.from_user.id
        quoted = update.message.reply_to_message.from_user.id
        if sender in get_admin_ids(bot, chat) and quoted not in get_admin_ids(bot, chat):
            bot.restrictChatMember(chat, quoted, can_send_messages=True, can_send_media_messages=True,
                                   can_send_other_messages=True, can_add_web_page_previews=True)
            update.message.reply_text(update.message.reply_to_message.from_user.first_name + " can speak now!")
        else:
            update.message.reply_text("Meh, either you're not an admin or the quoted user is one!")
    except AttributeError:
        update.message.reply_text(reply_to_message_id=update.message.message_id, text="Please quote a user to unmute!")


@run_async
def shrug(bot, update):
    bot.sendChatAction(update.message.chat_id, ChatAction.TYPING)
    time.sleep(1)
    bot.sendMessage(update.message.chat_id, reply_to_message_id=update.message.message_id, text="¯\_(ツ)_/¯")


class CustomCommands(CommandHandler):
    def check_update(self, update):
        if (isinstance(update, Update)
                and (update.message or update.edited_message and self.allow_edited)):
            message = update.message or update.edited_message

            if message.text and len(message.text) > 1 \
                    and any(message.text.startswith(start) for start in ('/', '!', '#')):
                command = message.text[1:].split(None, 1)[0].split('@')
                command.append(
                    message.bot.username)  # in case the command was send without a username

                if self.filters is None:
                    res = True
                elif isinstance(self.filters, list):
                    res = any(func(message) for func in self.filters)
                else:
                    res = self.filters(message)

                return res and (command[0].lower() in self.command
                                and command[1].lower() == message.bot.username.lower())
            else:
                return False

        else:
            return False


CommandHandler = CustomCommands

buildHandler = CommandHandler('build', build)
restartHandler = CommandHandler('restart', restart)
leaveHandler = CommandHandler('leave', leave)
helpHandler = CommandHandler('help', help)
idHandler = CommandHandler('id', id)
pullHandler = CommandHandler('pull', pull)
pushHandler = CommandHandler('push', push)
kickHandler = CommandHandler('kick', kick)
shrugHandler = CommandHandler('shrug', shrug)
syncHandler = CommandHandler('sync', sync)
pickHandler = CommandHandler('pick', pick)
cleanHandler = CommandHandler('clean', clean)
banHandler = CommandHandler('ban', ban)
unbanHandler = CommandHandler('unban', unban)
muteHandler = CommandHandler('mute', mute)
unmuteHandler = CommandHandler('unmute', unmute)

dispatcher.add_handler(buildHandler)
dispatcher.add_handler(restartHandler)
dispatcher.add_handler(leaveHandler)
dispatcher.add_handler(helpHandler)
dispatcher.add_handler(idHandler)
dispatcher.add_handler(pullHandler)
dispatcher.add_handler(pushHandler)
dispatcher.add_handler(idHandler)
dispatcher.add_handler(kickHandler)
dispatcher.add_handler(shrugHandler)
dispatcher.add_handler(syncHandler)
dispatcher.add_handler(pickHandler)
dispatcher.add_handler(cleanHandler)
dispatcher.add_handler(banHandler)
dispatcher.add_handler(unbanHandler)
dispatcher.add_handler(muteHandler)
dispatcher.add_handler(unmuteHandler)
dispatcher.add_handler(InlineQueryHandler(inlinequery))

updater.start_polling()
updater.idle()
