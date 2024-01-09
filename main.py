import requests
import json
import hashlib
import time
import hmac
from binance.client import Client
import re
import sys
import time
import os
from watchdog.observers import Observer
from telegram import Bot
from telegram import Update
from watchdog.events import FileSystemEventHandler
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime
from utils import format_quantity_for_binance
from utils import place_binance_order
from utils import get_binance_price
from utils import format_pair
from utils import sell_buy
from utils import clear_log_file
from utils import get_solde_coin
from utils import format_pair_usd
from utils import start_tab
from utils import check_balance_state
from utils import balance_only
from short_utils import place_binance_short_order
from short_utils import repay_short_binance
from short_utils import get_borrowed_amount

######################################################################################################################################

number_of_order_open = 0
number_of_order = 4
order_price = 500
balance = balance_only()

######################################################################################################################################
#telegram bot
chat_id = 1646361418
TOKEN = '6853456138:AAED_vhJ8qyOzLlcrLKNtj0LuT3dPZOmig4'
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

######################################################################################################################################

def start_info ():
    clear_log_file('/home/theolerich/projet/freqtrad/ft_userdata/user_data/logs/freqtrade.log')
    start_tab()
    print('valeur definie pour chaque ordre soumis : ', order_price)
    check_balance_state(order_price, balance, number_of_order)
    print('-------------------------------------------------------')
    print('\n')

start_info()


######################################################################################################################################

api_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
api_secret = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

######################################################################################################################################

def send_telegram_message(TOKEN, chat_id, message):
    api_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {'chat_id': chat_id, 'text': message}

    response = requests.get(api_url, params=params)

    # Vous pouvez vérifier le statut de la requête
    if response.status_code == 200:
        print("Message envoyé avec succès")
    else:
        print(f"Erreur lors de l'envoi du message. Code d'erreur : {response.status_code}")

######################################################################################################################################

def parse_trade_log(log_line):

    entry_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - freqtrade.persistence.trade_model - INFO - LIMIT_BUY has been fulfilled for Trade\(id=\d+, pair=(\w+/[\w/]+),', log_line)
    exit_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - freqtrade.freqtradebot - INFO - Exit for (\w+/[\w/]+) detected\. Reason: (.+)', log_line)

    if entry_match:
        timestamp = entry_match.group(1)
        pair = entry_match.group(2)
        signal_type = "Entry"
    elif exit_match:
        timestamp = exit_match.group(1)
        pair = exit_match.group(2)
        signal_type = "Exit"
    else:
        return None, None, None

    return timestamp, pair, signal_type

def parse_short_trade_log(log_line):

    entry_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - freqtrade.persistence.trade_model - INFO - LIMIT_BUY has been fulfilled for Trade\(id=\d+, pair=(\w+/[\w/]+),', log_line)
    exit_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - freqtrade.freqtradebot - INFO - Exit for (\w+/[\w/]+) detected\. Reason: (.+)', log_line)

    if entry_match:
        timestamp = entry_match.group(1)
        pair = entry_match.group(2)
        signal_type = "Entry"
    elif exit_match:
        timestamp = exit_match.group(1)
        pair = exit_match.group(2)
        signal_type = "Exit"
    else:
        return None, None, None

    return timestamp, pair, signal_type


def process_log_short(log_line):
    timestamp, pair, signal_type = parse_short_trade_log(log_line)
    if timestamp and pair and signal_type:
        price_currency = get_binance_price(format_pair(pair))
        quantity = order_price / price_currency
        quantity = format_quantity_for_binance(format_pair(pair), quantity)
        if signal_type == 'Entry' and number_of_order_open < number_of_order:
            number_of_order_open += 1
            print('BUY :',quantity,' of ', pair, ' for ', order_price)
            send_telegram_message(TOKEN, chat_id, 'BUY : '+str(quantity)+' of '+str(pair))
            place_binance_short_order(api_key, api_secret, format_pair(pair), quantity, 5)
            print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------------\
--------------------\n')
        else:
            number_of_order_open -= 1
            symbol = pair
            symbol = format_pair(symbol)
            quantity_sell =  get_borrowed_amount(api_key,api_secret,symbol)
            quantity_sell = format_quantity_for_binance(symbol, quantity_sell)
            send_telegram_message(TOKEN, chat_id, 'repay : '+str(quantity_sell)+' of '+str(pair))
            repay_short_binance(api_key, api_secret, symbol, 'BUY', 'MARKET', quantity_sell, 5)
            print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------------\
--------------------\n')



def process_log(log_line):
    timestamp, pair, signal_type = parse_trade_log(log_line)
    if timestamp and pair and signal_type:

        price_currency = get_binance_price(format_pair(pair))
        quantity = order_price / price_currency
        quantity = format_quantity_for_binance(format_pair(pair), quantity)
        if signal_type == 'Entry' and number_of_order_open < number_of_order:
            number_of_order_open += 1
            print('BUY :',quantity,' of ', pair, ' for ', order_price)
            send_telegram_message(TOKEN, chat_id, 'BUY : '+str(quantity)+' of '+str(pair))
            place_binance_order(api_key, api_secret, format_pair(pair), sell_buy(signal_type), 'MARKET', quantity, 5)
            print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------------\
--------------------\n')
        else:
            number_of_order_open -= 1
            formatted_pair = format_pair_usd(pair)
            sell_quantity = get_solde_coin(formatted_pair)
            sell_quantity = float(sell_quantity)
            sell_quantity =  sell_quantity * (1 - 0.001)
            sell_quantity = str(sell_quantity)
            sell_quantity = format_quantity_for_binance(format_pair(pair), sell_quantity)
            send_telegram_message(TOKEN, chat_id, 'SELL : '+str(sell_quantity)+' of '+str(pair))
            place_binance_order(api_key, api_secret, format_pair(pair), 'SELL', 'MARKET', sell_quantity, 5)
            print('--------------------------------------------------------------------------------------------------------------------------------------------------------------------------\
--------------------\n')

class LogHandlershort(FileSystemEventHandler):
    def __init__(self, log_file_path_short):
        self.log_file_path = log_file_path_short
        self.last_position = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        with open(self.log_file_path, 'r') as file:
            file.seek(self.last_position)
            new_logs = file.readlines()
            for log_line in new_logs:
                process_log_short(log_line)
            self.last_position = file.tell()


class LogHandler(FileSystemEventHandler):
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.last_position = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        with open(self.log_file_path, 'r') as file:
            file.seek(self.last_position)
            new_logs = file.readlines()
            for log_line in new_logs:
                process_log(log_line)
            self.last_position = file.tell()

log_file_path_short = '/home/theolerich/projet/freqtrad/ft_userdata/user_data/logs/freqtrade.log'
log_file_path = '/home/theolerich/projet/freqtrad/ft_userdata/user_data/logs/freqtrade.log'

observer = Observer()

log_handler_short = LogHandlershort(log_file_path_short)
log_handler = LogHandler(log_file_path)

observer.schedule(log_handler_short, path=os.path.dirname(log_file_path_short), recursive=False)
observer.schedule(log_handler, path=os.path.dirname(log_file_path), recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()


######################################################################################################################################
#telegram bot

updater.start_polling()
updater.idle()

######################################################################################################################################
