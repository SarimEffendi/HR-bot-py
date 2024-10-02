import os
from dotenv import load_dotenv

load_dotenv()

HIGHRISE_API_TOKEN = os.getenv("HIGHRISE_API_TOKEN")
HIGHRISE_ROOM_ID = os.getenv("HIGHRISE_ROOM_ID")
