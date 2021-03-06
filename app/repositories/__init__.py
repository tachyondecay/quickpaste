import random
from pymongo import MongoClient
from flask import g, current_app


def get_db() -> MongoClient:
    if 'mongo' not in g:
        g.mongo = MongoClient(
            current_app.config.get('MONGO_HOST', '127.0.0.1'),
            current_app.config.get('MONGO_PORT', 27017)
        )
        g.db = g.mongo[current_app.config.get('MONGO_DATABASE', 'quickpaste')]
    return g.db


def get_random_string(length, alphabet):
    r = random.SystemRandom()
    alphabet_len = len(alphabet)
    s = [alphabet[r.randrange(alphabet_len)] for i in range(length)]
    return ''.join(s)


def make_id():
    length = current_app.config.get('PASTE_ID_LENGTH', 7)
    alphabet = current_app.config.get(
        'LINK_ALPHABET',
        'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890_-'
    )
    return get_random_string(length, alphabet)


def insert_one(collection: str, d: dict):
    db = get_db()
    return db[collection].insert_one(d).inserted_id


def find_one(collection: str, d: dict):
    db = get_db()
    return db[collection].find_one(d)
