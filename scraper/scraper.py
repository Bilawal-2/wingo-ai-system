import random
import time
from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")
db = client.wingo
collection = db.results

while True:

    result = {
        "number": random.randint(0,9),
        "timestamp": time.time()
    }

    collection.insert_one(result)

    print("saved", result)

    time.sleep(60)