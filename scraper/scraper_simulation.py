import os
import random
import time
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "wingo")
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
collection_name = os.getenv("MONGODB_COLLECTION", "results")
collection = db[collection_name]

while True:
    min_num = int(os.getenv("RANDOM_NUMBER_MIN", 0))
    max_num = int(os.getenv("RANDOM_NUMBER_MAX", 9))
    sleep_interval = int(os.getenv("SCRAPER_SLEEP_INTERVAL", 60))

    result = {
        "number": random.randint(min_num, max_num),
        "timestamp": time.time()
    }

    collection.insert_one(result)

    print("saved", result)

    time.sleep(sleep_interval)