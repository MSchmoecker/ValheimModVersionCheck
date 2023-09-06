import logging

from src import bot, ModList, api
from readerwriterlock import rwlock

logging.basicConfig(format='[%(asctime)s %(levelname)-8s %(threadName)s] %(message)s', level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')

file_lock = rwlock.RWLockRead()
modlist: ModList = ModList(file_lock)

if __name__ == '__main__':
    api.run(modlist)
    bot.run(modlist)
