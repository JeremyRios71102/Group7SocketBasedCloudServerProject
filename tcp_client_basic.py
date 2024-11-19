import socket
import os

# Client Configuration
HOST = '10.128.0.2'  # Replace with your server's IP address
PORT = 3300
BUFFER_SIZE = 4096

def send_message(client_tcp, message):
    client_tcp.send(message.encode('utf-8'))
    data = client_tcp.recv(BUFFER_SIZE)
    print(f'The message received from the server: {data.decode("utf-8")}')

def send_file(client_tcp, filepath):
    if not os.path.exists(filepath):
        print('File does not exist.')
        return

    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    send_command = f'SEND_FILE {filename} {filesize}'
    client_tcp.send(send_command.encode('utf-8'))

    # Wait for server to be ready
    response = client_tcp.recv(BUFFER_SIZE).decode('utf-8')
    if response != 'READY':
        print('Server not ready to receive file.')
        return

    # Send the file data
    with open(filepath, 'rb') as f:
        while True:
            bytes_read = f.read(BUFFER_SIZE)
            if not bytes_read:
                break
            client_tcp.sendall(bytes_read)
    print(f'[*] Sent file {filename} to the server.')

    # Receive confirmation
    confirmation = client_tcp.recv(BUFFER_SIZE).decode('utf-8')
    print(f'Server response: {confirmation}')

def get_file(client_tcp, filename, save_dir='downloaded_files'):
    # Ensure the save directory exists
    os.makedirs(save_dir, exist_ok=True)

    send_command = f'GET_FILE {filename}'
    client_tcp.send(send_command.encode('utf-8'))

    # Receive server response
    response = client_tcp.recv(BUFFER_SIZE).decode('utf-8')
    if response.startswith('FILE'):
        _, filesize_str = response.split()
        try:
            filesize = int(filesize_str)
        except ValueError:
            print('Invalid file size received.')
            return

        # Acknowledge readiness to receive the file
        client_tcp.send('READY'.encode('utf-8'))

        # Receive the file data
        file_data = b''
        while len(file_data) < filesize:
            packet = client_tcp.recv(BUFFER_SIZE)
            if not packet:
                break
            file_data += packet

        # Save the file
        file_path = os.path.join(save_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(file_data)
        print(f'[*] Received file saved as {file_path}')

    elif response.startswith('ERROR'):
        print(f'Server error: {response}')
    else:
        print(f'Server response: {response}')

def setup_connection():
        client_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_tcp.connect((HOST, PORT))
        return client_tcp

if __name__ == '__main__':
    print('TCP Client')
    print('Commands:')
    print('1. send <message>        - Send a text message to the server.')
    print('2. sendfile <filepath>   - Send a text file to the server.')
    print('3. getfile <filename>    - Get a file from the server.')
    print('4. q                     - Quit.')

    while True:
        user_input = input('Enter command: ').strip()
        if user_input == 'q':
            print('Exiting.')
            break

        parts = user_input.split(maxsplit=1)
        if len(parts) == 0:
            continue

        command = parts[0].lower()

        if command == 'send' and len(parts) == 2:
            message = parts[1]
            try:
                with setup_connection() as client_tcp:
                    send_message(client_tcp, message)
            except Exception as e:
                print(f'Error: {e}')

        elif command == 'sendfile' and len(parts) == 2:
            filepath = parts[1]
            try:
                with setup_connection() as client_tcp:
                    send_file(client_tcp, filepath)
            except Exception as e:
                print(f'Error: {e}')

        elif command == 'getfile' and len(parts) == 2:
            filename = parts[1]
            try:
                with setup_connection() as client_tcp:
                    get_file(client_tcp, filename)
            except Exception as e:
                print(f'Error: {e}')

        else:
            print('Invalid command or missing arguments.')
