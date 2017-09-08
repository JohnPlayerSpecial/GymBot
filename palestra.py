import os
import telegram
from telegram.ext import *
from telegram import *
import logging
import timeit
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

TOKEN = '443645682:AAFjUhUmNIicWQxpgZP-fQWOVC3OF-EkvVk'
keyboard = [[InlineKeyboardButton("start", callback_data='start'),InlineKeyboardButton("stop", callback_data='stop'),]]
reply_markup = InlineKeyboardMarkup( keyboard )

'''
TOKEN_TELEGRAM = os.environ['TOKEN_TELEGRAM']
STRING_DB = os.environ['DATABASE_URL'].replace("postgres","pq")
db = postgresql.open(STRING_DB)
'''
dictTimingsByChatID = {}

def start(bot, update):
	welcomeText = "Welcome! \nUse /stopwatch to start the session\n/daily to get the daily total workout time\n/weekly to get the weekly total workout time, day by day\n" + u"\u2063" 
	bot.sendMessage(chat_id = update.message.chat_id , text = welcomeText)	

def getMyTimeZoneTime():
	HOUR_I_WANNA_GET_MESSAGE = 23
	MINUTES_I_WANNA_GET_MESSAGE = 45
	utc_offset_heroku = time.localtime().tm_gmtoff / 3600
	hour = HOUR_I_WANNA_GET_MESSAGE + ( int(utc_offset_heroku) - 2 ) # 2 is my offset
	time2 = datetime.time(hour = hour , minute = MINUTES_I_WANNA_GET_MESSAGE, second = 0)
	return time2
	
def getToday2Timestamp():
	utc_offset_heroku = time.localtime().tm_gmtoff
	timestamp = time.time()
	myTimestamp = timestamp - 2 * 3600
	start_str = time.strftime( "%m/%d/%Y" ) + " 00:00:00"
	end_str = time.strftime( "%m/%d/%Y ") + " 23:59:59"
	start_ts = int( time.mktime( time.strptime( start_str, "%m/%d/%Y %H:%M:%S" ) ) ) + utc_offset_heroku - 2 * 3600
	end_ts = int( time.mktime( time.strptime( end_str, "%m/%d/%Y %H:%M:%S" ) ) ) - 2 * 3600
	return start_ts, end_ts


def sendDailyWorkoutTime(bot, update):
	db = postgresql.open(STRING_DB)
	timestamp0, timestamp24 = getToday2Timestamp()
	ps = db.prepare("SELECT * FROM gymTimes WHERE chat_id={} AND timestamp BETWEEN {} AND {};".format( update.message.chat_id, timestamp0, timestamp24 ) )
	resultsList = ps()
	update.message.reply_text("""Total workout for this day: {}s.\nYou worked out {:2}h{:02}'{:02}''""".format(dailyWorkout, hours, minutes, seconds ))
	db.close()
	
def answerInlineQuery(bot,update):
	query = update.callback_query
	chat_id = update.callback_query.chat_id
	bot.answerCallbackQuery(callback_query_id = query.id)
	if (query.data == 'start'):
		start_time = time.time()
		if chat_id  not in dictTimingsByChatID:
			dictTimingsByChatID[ chat_id ] = time.time()	
		bot.editMessageText(chat_id = query.message.chat_id, message_id = query.message.message_id, text = welcomeText + "\n\nHai dato start alle ore ", reply_markup = reply_markup)
	if (query.data == 'stop'):
		if chat_id in dictTimingsByChatID:
			start = dictTimingsByChatID[ chat_id ]
			dictTimingsByChatID.pop( chat_id )
		else:
			return
		timestampDelta = time.time() - start
		elapsed = round( timestampDelta, 2)
		text = welcomeText + "\n\nHai dato stop alle ore.\nSono passati {} secondi".format(elapsed)
		bot.editMessageText( chat_id = query.message.chat_id, message_id = query.message.message_id, text = text, reply_markup = reply_markup)
		ps = db.prepare("INSERT INTO gymTimings (chat_id, start, stop, elapsed) VALUES ({},{},{},{}) ;".format( chat_id, start, stop, elapsed ) )
		ps()
		                     
updater = Updater(TOKEN)

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('daily', sendDailyWorkoutTime))
updater.dispatcher.add_handler(CommandHandler('weekly', sendWeeklyWorkoutTime))
updater.dispatcher.add_handler( CallbackQueryHandler( callback = answerInlineQuery ) )

#j.run_daily(sendDailyWorkoutTime,  time = getMyTimeZoneTime() )

updater.start_polling()
updater.idle()
