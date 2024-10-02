# bot/highrise_bot.py
import asyncio
from highrise import BaseBot, __main__, CurrencyItem, Item, Position, AnchorPosition, SessionMetadata, User
from highrise.__main__ import BotDefinition
from utils.music_player import MusicPlayer
from json import load, dump, JSONDecodeError
import os

class MyHighriseBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.chat_logs = []
        self.music_player = MusicPlayer()
        self.tip_data = {}
        self.bot_position = None
        self.load_tip_data()

    async def on_ready(self):
        try:
            print("Bot is ready and connected to the Highrise room!")
        except Exception as e:
            print(f"An error occurred in on_ready: {e}")

    async def on_chat(self, user: User, message: str) -> None:
        try:
            # Log chat messages
            self.chat_logs.append({"username": user.username, "message": message})
            print(f"Chat Log: {user.username}: {message}")

            # Save chat messages to logs/chat_logs.txt with UTF-8 encoding
            os.makedirs("logs", exist_ok=True)
            with open("logs/chat_logs.txt", "a", encoding="utf-8") as log_file:
                log_file.write(f"{user.username}: {message}\n")

            # Handling different commands
            if message.startswith("!say "):
                bot_message = message[len("!say "):]
                await self.highrise.chat(bot_message)

            elif message.startswith("!play "):
                url = message.split(" ", 1)[1]
                await self.highrise.chat("Playing music from the provided URL...")
                self.music_player.play_music(url)

            elif message == "!stop":
                self.music_player.stop_music()
                await self.highrise.chat("Music playback stopped.")

            elif message == "!top":
                top_tippers = self.get_top_tippers()
                if top_tippers:
                    formatted_tippers = [f"{i + 1}. {data['username']} ({data['total_tips']}g)" for i, (_, data) in enumerate(top_tippers)]
                    top_tipper_message = "Top Tippers:\n" + "\n".join(formatted_tippers)
                    await self.highrise.chat(top_tipper_message)
                else:
                    await self.highrise.chat("No tips received yet.")

            elif message == "!wallet":
                wallet = await self.highrise.get_wallet()
                gold = next((c.amount for c in wallet.content if c.type == 'gold'), 0)
                await self.highrise.chat(f"I have {gold}g in my wallet.")

            elif message.startswith("!get "):
                username = message.split(" ", 1)[1].replace("@", "")
                tip_amount = self.get_user_tip_amount(username)
                if tip_amount is not None:
                    await self.highrise.chat(f"{username} has tipped {tip_amount}g")
                else:
                    await self.highrise.chat(f"{username} hasn't tipped.")

            elif message == "!set":
                set_position = await self.set_bot_position(user.id)
                await self.highrise.chat(set_position)

        except Exception as e:
            print(f"An error occurred while processing the chat message: {e}")
            await self.highrise.chat("An error occurred while processing your request. Please try again.")

    async def on_tip(self, sender: User, receiver: User, tip: CurrencyItem | Item) -> None:
        try:
            if isinstance(tip, CurrencyItem) and receiver.id == self.bot_id:
                print(f"{sender.username} tipped {tip.amount}g -> {receiver.username}")
                if sender.id not in self.tip_data:
                    self.tip_data[sender.id] = {"username": sender.username, "total_tips": 0}
                self.tip_data[sender.id]['total_tips'] += tip.amount
                self.write_tip_data(sender, tip.amount)
        except Exception as e:
            print(f"An error occurred while processing the tip: {e}")

    async def on_user_join(self, user: User, position: Position) -> None:
        try:
            greeting_message = f"Welcome to the room, {user.username}!"
            await self.highrise.chat(greeting_message)
            print(f"{user.username} joined the room")
        except Exception as e:
            print(f"An error occurred when welcoming the user: {e}")

    async def on_user_leave(self, user: User) -> None:
        try:
            print(f"{user.username} left the room")
        except Exception as e:
            print(f"An error occurred when handling user leave: {e}")

    async def on_start(self, session_metadata: SessionMetadata) -> None:
        try:
            print("Bot Connected")
            self.bot_id = session_metadata.user_id
        except Exception as e:
            print(f"An error occurred during bot start: {e}")

    def get_top_tippers(self):
        try:
            sorted_tippers = sorted(self.tip_data.items(), key=lambda x: x[1]['total_tips'], reverse=True)
            return sorted_tippers[:10]
        except Exception as e:
            print(f"An error occurred while getting top tippers: {e}")
            return []

    def get_user_tip_amount(self, username):
        try:
            for _, user_data in self.tip_data.items():
                if user_data['username'].lower() == username.lower():
                    return user_data['total_tips']
            return None
        except Exception as e:
            print(f"An error occurred while getting user tip amount: {e}")
            return None

    async def set_bot_position(self, user_id) -> str:
        try:
            room_users = await self.highrise.get_room_users()
            for room_user, pos in room_users.content:
                if user_id == room_user.id and isinstance(pos, Position):
                    position = pos
                    with open("./data.json", "r+") as file:
                        data = load(file)
                        data["bot_position"] = {
                            "x": position.x,
                            "y": position.y,
                            "z": position.z,
                            "facing": position.facing
                        }
                        file.seek(0)
                        dump(data, file)
                        file.truncate()

                    set_position = Position(position.x, position.y + 0.0000001, position.z, facing=position.facing)
                    await self.highrise.teleport(self.bot_id, set_position)
                    await self.highrise.teleport(self.bot_id, position)
                    await self.highrise.walk_to(position)
                    return "Updated bot position."
            return "Failed to update bot position."
        except Exception as e:
            print(f"Error setting bot position: {e}")
            return "Error occurred while setting the bot's position."

    def write_tip_data(self, user: User, tip: int) -> None:
        try:
            with open("./data.json", "r+") as file:
                data = load(file)
                user_data = data["users"].get(user.id, {"total_tips": 0, "username": user.username})
                user_data["total_tips"] += tip
                data["users"][user.id] = user_data
                file.seek(0)
                dump(data, file)
                file.truncate()
        except JSONDecodeError:
            print("Error: JSON file is corrupted. Reinitializing data.")
            self.initialize_data_file()
        except Exception as e:
            print(f"An error occurred while writing tip data: {e}")

    def load_tip_data(self) -> None:
        try:
            if not os.path.exists("./data.json"):
                self.initialize_data_file()
            with open("./data.json", "r") as file:
                data = load(file)
                self.tip_data = data["users"]
        except JSONDecodeError:
            print("Error: JSON file is corrupted. Reinitializing data.")
            self.initialize_data_file()
        except Exception as e:
            print(f"An error occurred while loading tip data: {e}")

    def initialize_data_file(self):
        try:
            with open("./data.json", "w") as file:
                dump({"users": {}, "bot_position": {"x": 0, "y": 0, "z": 0, "facing": "FrontRight"}}, file)
            self.tip_data = {}
        except Exception as e:
            print(f"An error occurred while initializing data file: {e}")

    async def run_bot(self, room_id, api_key) -> None:
        try:
            definitions = [BotDefinition(self, room_id, api_key)]
            await __main__.main(definitions)
        except Exception as e:
            print(f"An error occurred while running the bot: {e}")
