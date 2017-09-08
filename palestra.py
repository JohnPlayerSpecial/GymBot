import os
import telegram
from telegram.ext import *
from telegram import *
import logging
import timeit
import time
import postgresql
import datetime
from emoji import emojize
import emoji
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

TOKEN_TELEGRAM = os.environ['TOKEN_TELEGRAM']
STRING_DB = os.environ['DATABASE_URL'].replace("postgres","pq")
APP_NAME = os.environ['APP_NAME']
PORT = int( os.environ['PORT'] )

keyboard = [[InlineKeyboardButton("start", callback_data='start'),InlineKeyboardButton("stop", callback_data='stop'),]]
reply_markup = InlineKeyboardMarkup( keyboard )
dictTimingsByChatID = {}
utc_offset_heroku = time.localtime().tm_gmtoff
beginSessionText = "Tap <b>start</b> to begin session\nTap <b>stop</b> to stop the session"


db = postgresql.open(STRING_DB)
STRING_QUERY = "CREATE TABLE IF NOT EXISTS gymTimings ( id SERIAL PRIMARY KEY, chat_id INT, start FLOAT DEFAULT 0, stop FLOAT DEFAULT 0, elapsed FLOAT DEFAULT 0);"
ps = db.prepare( STRING_QUERY )
ps()
db.close()


def start(bot, update):
	welcomeText = "<b>Welcome!</b>\nUse:\n /stopwatch  to start the session\n/daily get daily total workout time\n/weekly get weekly total workout time\n" + u"\u2063" 
	bot.sendMessage(chat_id = update.message.chat_id , text = welcomeText, parse_mode="Html")	
	#bot.sendMessage(chat_id = update.message.chat_id , text = emojize(":cake:", use_aliases=True) )

def getMyTimeZoneTime():
	HOUR_I_WANNA_GET_MESSAGE = 23
	MINUTES_I_WANNA_GET_MESSAGE = 45
	utc_offset_heroku = time.localtime().tm_gmtoff / 3600
	hour = HOUR_I_WANNA_GET_MESSAGE + ( int(utc_offset_heroku) - 2 ) # 2 is my offset
	time2 = datetime.time(hour = hour , minute = MINUTES_I_WANNA_GET_MESSAGE, second = 0)
	return time2

def getHumanElapsedTime( elapsed ):
	return "{}h{:02}m{:02}s".format( int( elapsed//3600 ), int(elapsed // 60)%60, elapsed%60 ) 
	
def getToday2Timestamp():
	utc_offset_heroku = time.localtime().tm_gmtoff
	print(utc_offset_heroku)
	start_str = time.strftime( "%m/%d/%Y" ) + " 00:00:00"
	end_str = time.strftime( "%m/%d/%Y ") + " 23:59:59"
	start_ts = int( time.mktime( time.strptime( start_str, "%m/%d/%Y %H:%M:%S" ) ) ) - utc_offset_heroku + 2 * 3600
	end_ts = int( time.mktime( time.strptime( end_str, "%m/%d/%Y %H:%M:%S" ) ) )     - utc_offset_heroku + 2 * 3600
	return start_ts, end_ts

def sendStopwatch(bot, update):
	chat_id = update.message.chat_id
	text = beginSessionText + "\n" + u"\u2063" + "\n" + u"\u2063" + "\n" + u"\u2063" + "\n" + u"\u2063"
	bot.sendMessage(chat_id = chat_id, text = text, reply_markup = reply_markup, parse_mode = "Html")
	
	
def sendDailyWorkoutTime(bot, update):
	db = postgresql.open(STRING_DB)
	timestamp0, timestamp24 = getToday2Timestamp()
	ps = db.prepare("SELECT * FROM gymTimings WHERE chat_id={} AND start > {} AND stop < {};".format( update.message.chat_id, timestamp0, timestamp24 ) )
	total = round( sum( [item[4] for item in ps()] ) )
	chat_id = update.message.chat_id
	today = datetime.datetime.fromtimestamp( time.time() - utc_offset_heroku + 2 * 3600 ).strftime('%A %d %b %Y')
	text = "<b>{}</b>\n\nToday total workout seconds: <b>{}s.</b>\nYou worked out for <b>{}</b>".format(today,total, getHumanElapsedTime( total ) )
	bot.sendMessage(chat_id = chat_id, text = text, parse_mode = "Html")
	db.close()

def sendWeeklyWorkoutTime(bot, update):	
	chat_id = update.message.chat_id
	totalList = []
	db = postgresql.open(STRING_DB)
	todayWeekDay = datetime.datetime.fromtimestamp( time.time() - utc_offset_heroku + 2 * 3600  ).weekday() 
	timestampToday0, timestampToday24 = getToday2Timestamp()
	for i in range( todayWeekDay + 1 ): # + 1 = get also today
		timestamp0 =   timestampToday0  -  86400 * ( todayWeekDay - i )
		timestamp24  = timestampToday24 -  86400 * ( todayWeekDay - i )
		ps = db.prepare("SELECT * FROM gymTimings WHERE chat_id={} AND start > {} AND stop < {};".format( update.message.chat_id, timestamp0, timestamp24 ) )
		ps()
		totalList.append( round( sum( [item[4] for item in ps()] ) ) )
		weekNumber = datetime.datetime.fromtimestamp( timestamp0 ).strftime('%W')
	text = "*** Here are the results for week #{} ***\n\n".format(weekNumber)
	bestDay = max(totalList) 
	worstDay = min(totalList) 
	for i in range( todayWeekDay + 1 ): # + 1 = get also today
		timestamp0 =   timestampToday0  -  86400 * ( todayWeekDay - i )
		timestamp24  = timestampToday24 -  86400 * ( todayWeekDay - i )
		today = datetime.datetime.fromtimestamp( timestamp0 ).strftime('%a %d %b')
		if totalList[i] == bestDay:
			string = " :clap::clap::clap: ``` {}: {}```\n".format( today, getHumanElapsedTime(totalList[i]) )
			text += emojize( string, use_aliases=True) 
			continue
		if totalList[i] == worstDay:
			string = " :fearful::fearful::fearful: ``` {}: {}```\n".format( today, getHumanElapsedTime(totalList[i]) )
			text += emojize( string, use_aliases=True) 
			continue
		string = " :muscle::muscle::muscle: ``` {}: {}```\n".format( today, getHumanElapsedTime(totalList[i]) )
		text += emojize( string, use_aliases=True) 
	text += "\n***Total workout this week: {}***".format( getHumanElapsedTime( sum(totalList) ) )
	bot.sendMessage(chat_id = chat_id, text = text, parse_mode = "Markdown")
	db.close()

def answerInlineQuery(bot,update):
	query = update.callback_query
	chat_id = update.callback_query.message.chat_id
	bot.answerCallbackQuery(callback_query_id = query.id)
	if (query.data == 'start'):
		start_time = time.time() - utc_offset_heroku + 2 * 3600 
		if chat_id  not in dictTimingsByChatID:
			dictTimingsByChatID[ chat_id ] = start_time	
		startHour = datetime.datetime.fromtimestamp(start_time).strftime('%H:%M:%S')
		text = beginSessionText + "\n\nHai dato <b>start</b> alle ore <b>{}</b>".format( startHour ) + "\n" + u"\u2063" + "\n" + u"\u2063" 
		bot.editMessageText(chat_id = chat_id, message_id = query.message.message_id, text = text, reply_markup = reply_markup, parse_mode = "Html")
	if (query.data == 'stop'):
		if chat_id in dictTimingsByChatID:
			start = dictTimingsByChatID[ chat_id ]
			dictTimingsByChatID.pop( chat_id )
		else:
			return
		stop = time.time() - utc_offset_heroku + 2 * 3600 
		timestampDelta = stop - start
		elapsed = round( timestampDelta, 2)
		startHour = datetime.datetime.fromtimestamp(start).strftime('%H:%M:%S')
		stopHour = datetime.datetime.fromtimestamp(stop).strftime('%H:%M:%S')
		text = beginSessionText + "\n\nHai dato <b>start</b> alle ore <b>{}</b>".format( startHour) + "\nHai dato <b>stop</b> alle ore <b>{}</b>.\nSono passati <b>{}</b>".format(stopHour, getHumanElapsedTime( elapsed ) )
		bot.editMessageText( chat_id = query.message.chat_id, message_id = query.message.message_id, text = text, reply_markup = reply_markup, parse_mode = "Html")
		db = postgresql.open(STRING_DB)
		ps = db.prepare("INSERT INTO gymTimings (chat_id, start, stop, elapsed) VALUES ({},{},{},{}) ;".format( chat_id, start, stop, elapsed ) )
		ps()
		db.close()
		                     
updater = Updater(TOKEN_TELEGRAM)
updater.start_webhook(listen="0.0.0.0", port=PORT, url_path = TOKEN_TELEGRAM)
updater.bot.set_webhook("https://{}.herokuapp.com/".format(APP_NAME) + TOKEN_TELEGRAM)

updater.dispatcher.add_handler(CommandHandler('start', start) )
updater.dispatcher.add_handler(CommandHandler('daily', sendDailyWorkoutTime) )
updater.dispatcher.add_handler(CommandHandler('weekly', sendWeeklyWorkoutTime) )
updater.dispatcher.add_handler(CommandHandler('stopwatch', sendStopwatch) )
updater.dispatcher.add_handler( CallbackQueryHandler( callback = answerInlineQuery ) )

#j.run_daily(sendDailyWorkoutTime,  time = getMyTimeZoneTime() )

updater.idle()
