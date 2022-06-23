import logging
import threading

from src import bot, decompile
from readerwriterlock import rwlock


logging.basicConfig(format='[%(asctime)s %(levelname)-8s %(threadName)s] %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

if __name__ == '__main__':
    file_lock = rwlock.RWLockRead()
    bot.run(file_lock)
