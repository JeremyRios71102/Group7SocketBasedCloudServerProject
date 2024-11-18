#!/usr/bin/env python3
import socket
import threading
import os

# Server Configuration
HOST = '10.128.0.2'  # Replace with your server's IP address
PORT = 3300
BUFFER_SIZE = 4096
DASHES = '----> '

# Directory to save received files
RECEIVED_FILES_DIR = 'received_files'
os.makedirs(RECEIVED_FILES_DIR, exist_ok=True)

def handle_client(connection, addr):
    print(f'[*] Established connection from IP {addr[0]} port: {addr[1]}')
    try:
        while True:
            data = connection.recv(BUFFER_SIZE)
            if not data:
                print(f'[*] Connection closed by {addr[0]}:{addr[1]}')
                break

            # Decode the received data
            message = data.decode('utf-8')

            if message.startswith('SEND_FILE'):
                # Protocol: SEND_FILE filename size
                parts = message.split()
                if len(parts) != 3:
                    connection.send('Invalid SEND_FILE command format.'.encode('utf-8'))
                    continue

                _, filename, filesize_str = parts
                try:
                    filesize = int(filesize_str)
                except ValueError:
                    connection.send('Invalid file size.'.encode('utf-8'))
                    continue

                connection.send('READY'.encode('utf-8'))

                # Receive the file data
                file_data = b''
                while len(file_data) < filesize:
                    packet = connection.recv(BUFFER_SIZE)
                    if not packet:
                        break
                    file_data += packet

                # Save the file
                file_path = os.path.join(RECEIVED_FILES_DIR, f'{addr[0]}_{filename}')
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                print(f'[*] Received file from {addr[0]}:{addr[1]} saved as {file_path}')
                connection.send(f'File {filename} received successfully.'.encode('utf-8'))

            elif message.startswith('GET_FILE'):
                # Protocol: GET_FILE filename
                parts = message.split()
                if len(parts) != 2:
                    connection.send('Invalid GET_FILE command format.'.encode('utf-8'))
                    continue

                _, filename = parts
                file_path = os.path.join(RECEIVED_FILES_DIR, filename)
                if not os.path.exists(file_path):
                    connection.send('ERROR: File does not exist.'.encode('utf-8'))
                    continue

                filesize = os.path.getsize(file_path)
                connection.send(f'FILE {filesize}'.encode('utf-8'))

                # Wait for the client to be ready
                ack = connection.recv(BUFFER_SIZE).decode('utf-8')
                if ack != 'READY':
                    continue

                # Send the file data
                with open(file_path, 'rb') as f:
                    while True:
                        bytes_read = f.read(BUFFER_SIZE)
                        if not bytes_read:
                            break
                        connection.sendall(bytes_read)
                print(f'[*] Sent file {filename} to {addr[0]}:{addr[1]}')

            else:
                print(f'[*] Data received from {addr[0]}:{addr[1]}: {message}')
                response = DASHES + message
                connection.send(response.encode('utf-8'))

    except Exception as e:
        print(f'[!] Exception handling client {addr[0]}:{addr[1]}: {e}')
    finally:
        connection.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_tcp:
        server_tcp.bind((HOST, PORT))
        server_tcp.listen(5)
        print(f'[*] Server listening on {HOST}:{PORT}')

        while True:
            connection, addr = server_tcp.accept()
            client_thread = threading.Thread(target=handle_client, args=(connection, addr), daemon=True)
            client_thread.start()
            print(f'[*] Started thread for {addr[0]}:{addr[1]}')

if __name__ == '__main__':
    start_server()

# tcp_server_basic.py
#!/usr/bin/env python3
import socket

# host binds to local server ip
host = '10.128.0.2'
port = 3300
BUFFER_SIZE = 1024
dashes = '----> '

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_tcp:
    server_tcp.bind((host, port))
    # wait for client connection
    while True:
        server_tcp.listen(6)
        print('[*] Waiting for connection')
        # establish client connection
        connection, addr = server_tcp.accept()
        with connection:
            print(f'[*] Established connection from IP {addr[0]} port: {addr[1]}')
            while True:
                # receive bytes
                data = connection.recv(BUFFER_SIZE)
                # verify received data
                if not data:
                    break
                else:
                    # convert to string
                    print('[*] Data received: {}'.format(data.decode('utf-8')))
                    connection.send(dashes.encode('utf-8') + data)  # echo data back to origin