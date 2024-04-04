import socket
import threading
import queue
import sys
import time

class ChatClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None  # Initialize socket as None for reinitialization during reconnect
        self.nickname = None
        self.running = True
        self.msg_queue = queue.Queue()
        self.max_retries = 5  # Maximum number of reconnection attempts
        self.waiting_for_nickname_confirmation = False  # Flag to track nickname confirmation status

    def set_nickname(self):
        # Prompts the user for a nickname and sends it to the server.
        if not self.waiting_for_nickname_confirmation:
            self.nickname = input("Enter your nickname: ")
            self.send_message(f"/nickname {self.nickname}")
            self.waiting_for_nickname_confirmation = True  # Waiting for server confirmation
        else:
            print("Waiting for nickname confirmation...")

    def receive_messages(self):
        # Listens for incoming messages from the server and prints them.
        while self.running:
            try:
                message = self.socket.recv(1024).decode('utf-8')
                if message:
                    print(f"\n{message}")
                    # Check for pending messages and prompt the user if they are typing
                    if not self.msg_queue.empty():
                        print("", end="", flush=True)
                    self.msg_queue.put(message)
            except Exception as e:
                print(f"Receiving message failed: {e}")
                self.running = False
                break

    def send_message(self, message):
        # Sends a message to the server.
        try:
            self.socket.send(message.encode('utf-8'))
            print(f"You: {message}")
        except Exception as e:
            print(f"Sending message failed: {e}")

    def handle_join_channel(self):
        # Handles joining a chat channel and sending messages within it.
        channel_name = input("Enter the channel name you want to join: ")
        self.send_message(f"/join {channel_name}")
        print(f"You have joined the channel: {channel_name}. Type '/quit' to exit.")
        
        while True:
            message = input(f"{self.nickname}@{channel_name}: ")
            if message == "/quit":
                break
            else:
                self.send_message(message)

    def show_menu(self):
        # Displays the main menu and handles user input for different actions.
        while self.running:
            print("\nMenu:")
            print("1. Change Nickname")
            print("2. Join Public Chat")
            print("3. Private Message")
            print("4. Join a Channel")
            print("5. Disconnect")
            choice = input("Enter choice: ")

            if choice == "1":
                new_nickname = input("Enter new nickname: ")
                self.send_message(f"/nickname {new_nickname}")
                self.nickname = new_nickname
            elif choice == "2":
                self.send_message("/join public")
                self.handle_user_input()
            elif choice == "3":
                self.handle_private_message()
            elif choice == "4":  
                self.handle_join_channel()
            elif choice == "5":
                self.disconnect()
                break
            else:
                print("Invalid choice. Please try again.")

    def handle_private_message(self):
        # Handles sending private messages to a specific user.
        target_nickname = input("Enter the nickname for private message: ")
        print("You are now in private chat with " + target_nickname + ". Type '/quit' to return to menu.")
        while self.running:
            message = input("Your message: ")
            if message.lower() == "/quit":
                break
            else:
                try:
                    formatted_message = f"/private {target_nickname} {message}"
                    self.socket.send(formatted_message.encode('utf-8'))
                    print(f"To {target_nickname}: {message}")
                except Exception as e:
                    print(f"Sending message failed: {e}")

    def disconnect(self):
        # Disconnects from the server and stops the client.""
        self.running = False
        self.send_message("/quit")
        self.socket.close()
        print("Disconnected from server.")

    def handle_user_input(self):
        # Handles user input in public chat.
        print("You are now in the public chat. Type '/quit' to return to menu.")
        while self.running:
            user_input = input("Your message: ")
            if user_input.lower() == "/quit":
                break
            else:
                self.send_message(user_input)

    def connect_to_server(self):
        # Attempts to connect to the server and starts the message receiving thread.
        self.running = True
        retry_count = 0
        while self.running and retry_count < self.max_retries:
            try:
                if self.socket is not None:
                    self.socket.close()
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                threading.Thread(target=self.receive_messages, daemon=True).start()
                self.set_nickname()
                self.show_menu()
                break
            except Exception as e:
                retry_count += 1
                print(f"Connection failed, retrying ({retry_count}/{self.max_retries})...")
                time.sleep(5)
        if retry_count == self.max_retries:
            print("Failed to connect after several attempts. Exiting...")
            self.running = False

if __name__ == "__main__":
    host = input("Enter server IP: ")
    port = 12345
    client = ChatClient(host, port)
    client.connect_to_server()
