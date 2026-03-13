from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("mongodb+srv://qasoskorbek8_db_user:CFQuBXFhgFSdHRtN@cluster0.m1tezqo.mongodb.net/start") 

client = AsyncIOMotorClient(MONGO_URL)
db = client["order_bot"]

orders_collection = db["orders"]