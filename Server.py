import socket
import threading
import queue
import sys
import time  

class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = {}  # Stores client connections
        self.nicknames = {}  # Maps connections to nicknames
        self.channels = {"public": []}  # Maps channel names to lists of client connections

    def start_server(self):
        # Starts the server and listens for incoming connections.
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # choose TCP
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        print("Server listening on port", self.port)
        
        while True:
            conn, addr = server_socket.accept()
            print("Connected by", addr)
            threading.Thread(target=self.handle_client, args=(conn,)).start()

    def broadcast(self, message, channel="public", exclude=None):
        # Sends a message to all clients in a specific channel, except the sender.
        clients = self.channels.get(channel, [])
        for client in clients:
            if client != exclude:
                try:
                    client.send(message.encode('utf-8'))
                except:
                    self.remove_client(client)

    def private_message(self, message, sender_conn, recipient_nickname):
        print("Current nicknames and connections:")
        for nick, conn in self.nicknames.items():
            print(f"Nickname: '{nick}', Connection: {conn}")

        print(f"Attempting to find recipient: '{recipient_nickname}'")
        recipient_nickname_lower = recipient_nickname.lower().strip()
        recipient_conn = self.nicknames.get(recipient_nickname_lower, None)

        if recipient_conn:
            # Get the sender nickname directly from self.clients
            sender_nickname = self.clients.get(sender_conn, None)
            
            if sender_nickname:
                try:
                    formatted_message = f"{sender_nickname} (private): {message}"
                    recipient_conn.send(formatted_message.encode('utf-8'))
                    sender_conn.send(f"Message sent to {recipient_nickname}: {message}".encode('utf-8'))
                    print(f"Private message from {sender_nickname} to {recipient_nickname}: {message}")
                except Exception as e:
                    sender_conn.send(f"Failed to send message to {recipient_nickname}. Error: {e}".encode('utf-8'))
                    print(f"Error sending private message: {e}")
            else:
                print("Error: Sender's nickname not found.")
                sender_conn.send("Error: Your nickname was not found in the server.".encode('utf-8'))
        else:
            print(f"User not found: '{recipient_nickname}'")
            sender_conn.send(f"User {recipient_nickname} not found.".encode('utf-8'))

    def handle_client(self, conn):
        # Handles communication with a connected client.
        try:
            conn.send("Please enter your nickname: ".encode('utf-8'))
            nickname_command = conn.recv(1024).decode('utf-8').strip()
            if nickname_command.startswith("/nickname"):
                _, nickname = nickname_command.split(maxsplit=1)  
                nickname_lower = nickname.lower()  
            else:
                conn.send("Invalid nickname format. Closing connection.".encode('utf-8'))
                conn.close()
                return

            print(f"Storing nickname: '{nickname}', normalized as '{nickname_lower}'")
            self.clients[conn] = nickname  # Store the original nickname
            self.nicknames[nickname_lower] = conn  # Use lowercase nicknames when mapping
            self.channels["public"].append(conn)
            self.broadcast(f"{nickname} joined the chat!", "public", conn)

            while True:
                try:
                    message = conn.recv(1024).decode('utf-8')
                    if message.startswith("/nickname"):
                        _, new_nickname = message.split(maxsplit=1)
                        if new_nickname.lower() in self.nicknames:
                            conn.send("Nickname already taken. Please choose another one.".encode('utf-8'))
                        else:
                            old_nickname = self.clients[conn]
                            self.broadcast(f"{old_nickname} changed their nickname to {new_nickname}", exclude=conn)
                            self.nicknames[new_nickname.lower()] = conn
                            del self.nicknames[old_nickname.lower()]
                            self.clients[conn] = new_nickname
                            conn.send("Nickname change successful.".encode('utf-8'))
                    elif message.startswith("/private"):
                        _, recipient_nickname, private_message = message.split(' ', 2)
                        self.private_message(private_message, conn, recipient_nickname)
                    elif message.startswith("/join"):
                        _, channel_name = message.split()
                        self.change_channel(conn, channel_name)
                    elif message == "/quit":
                        self.remove_client(conn)
                        break
                    else:
                        current_channel = self.get_client_channel(conn)
                        if current_channel:
                            self.broadcast(f"{nickname}: {message}", channel=current_channel, exclude=conn)
                except socket.timeout:
                    print(f"Timeout: Client {nickname} has not sent any data for a while.")
                    break
                except socket.error as e:
                    print(f"Socket error: Client {nickname} connection error {e}.")
                    break
                except Exception as e:
                    print(f"Unexpected error: Error handling message from client {nickname}: {e}.")
        except Exception as e:
            print(f"Error setting up connection for client: {e}")
        finally:
            self.remove_client(conn)

    def change_channel(self, conn, new_channel):
        # Moves a client from one channel to another.
        for channel, clients in self.channels.items():
            if conn in clients:
                clients.remove(conn)
                break

        if new_channel not in self.channels:
            self.channels[new_channel] = []
        self.channels[new_channel].append(conn)
        self.broadcast(f"{self.clients[conn]} joined {new_channel}", channel=new_channel, exclude=conn)

    def get_client_channel(self, conn):
        # Returns the channel a client is currently in.
        for channel, clients in self.channels.items():
            if conn in clients:
                return channel
        return "public"

    def remove_client(self, conn):
        # Removes a client from the server.
        try:
            nickname = self.clients.pop(conn, None)
            if nickname:
                self.nicknames.pop(nickname.lower(), None)
                for channel in self.channels.values():
                    if conn in channel:
                        channel.remove(conn)
                conn.close()
                self.broadcast(f"{nickname} left the chat.", "public")
        except Exception as e:
            print(f"Error removing client: {e}")

if __name__ == '__main__':
    chat_server = ChatServer('localhost', 12345)
    chat_server.start_server()
