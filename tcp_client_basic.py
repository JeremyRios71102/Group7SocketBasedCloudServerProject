import socket
import os
from time import perf_counter as pc
from tqdm import tqdm
from network_analysis import NetworkMetrics

# Client Configuration
HOST = '10.128.0.2'  # Replace with your server's IP address
PORT = 3300
BUFFER_SIZE = 4096

def send_message(message):
    client_tcp = setup_connection()
    try:
        client_tcp.send(message.encode('utf-8'))
        data = client_tcp.recv(BUFFER_SIZE)
        print(f'The message received from the server:\n{data.decode("utf-8")}')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        client_tcp.close()

def send_file(filepath):
    if not os.path.exists(filepath):
        print(f'File does not exist: {filepath}')
        return

    client_tcp = setup_connection()
    try:
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
        tic = pc()
        with open(filepath, 'rb') as f:
            progress_bar = tqdm(total=filesize, unit='B', unit_scale=True, desc=f'Sending {filename}')
            while True:
                bytes_read = f.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                client_tcp.sendall(bytes_read)
                progress_bar.update(len(bytes_read))
            progress_bar.close()
        toc = pc()
        print(f'[*] Sent file {filename} to the server.')
        
        # Calculating and printing the network metrics
        metrics = NetworkMetrics()
        time = round(toc - tic, 2)
        megabyte = 1000000
        speed = (filesize/megabyte) / time
        metrics.log_transfer(send_command, filename, filesize, time, speed)
        print(f'Network Metrics:\n{metrics.data_transfer_log}')

        # Receive confirmation
        confirmation = client_tcp.recv(BUFFER_SIZE).decode('utf-8')
        print(f'Server response: {confirmation}')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        client_tcp.close()

def get_file(filename, save_dir='downloaded_files'):
    client_tcp = setup_connection()
    try:
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
            tic = pc()
            progress_bar = tqdm(total=filesize, unit='B', unit_scale=True, desc=f'Receiving {filename}')
            file_data = b''
            while len(file_data) < filesize:
                packet = client_tcp.recv(BUFFER_SIZE)
                if not packet:
                    break
                file_data += packet
                progress_bar.update(len(packet))
            progress_bar.close()
            toc = pc()

            # Calculating and printing the network metrics
            metrics = NetworkMetrics()
            time = round(toc - tic, 2)
            megabyte = 1000000
            speed = (filesize/megabyte) / time
            metrics.log_transfer(send_command, filename, filesize, time, speed)
            print(f'Network Metrics:\n{metrics.data_transfer_log}')

            # Save the file
            file_path = os.path.join(save_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            print(f'[*] Received file saved as {filename} in {save_dir}.')

        elif response.startswith('ERROR'):
            print(f'Server error: {response}')
        else:
            print(f'Server response: {response}')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        client_tcp.close()

def delete_file(filename):
    client_tcp = setup_connection()
    try:
        send_command = f'DELETE {filename}'
        client_tcp.send(send_command.encode('utf-8'))

        # Receive server response
        response = client_tcp.recv(BUFFER_SIZE).decode('utf-8')
        print(f'Server response: {response}')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        client_tcp.close()

def directory_listing():
    client_tcp = setup_connection()
    try:
        client_tcp.send('DIR'.encode('utf-8'))

        # Receive directory listing
        response = client_tcp.recv(BUFFER_SIZE).decode('utf-8')
        print('Server directory listing:')
        print(response)
    except Exception as e:
        print(f'Error: {e}')
    finally:
        client_tcp.close()

def manage_subfolder(action, path):
    client_tcp = setup_connection()
    try:
        send_command = f'SUBFOLDER {action.upper()} {path}'
        client_tcp.send(send_command.encode('utf-8'))

        # Receive server response
        response = client_tcp.recv(BUFFER_SIZE).decode('utf-8')
        print(f'Server response: {response}')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        client_tcp.close()

def setup_connection():
    client_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_tcp.connect((HOST, PORT))
    return client_tcp

if __name__ == '__main__':
    print('TCP Client')
    print('Commands:')
    print('1. send <message>                 - Send a text message to the server.')
    print('2. sendfile <filepath>            - Send a text file to the server.')
    print('3. getfile <filename>             - Get a file from the server.')
    print('4. delete <filename>              - Delete a file from the server.')
    print('5. dir                            - List files and directories on the server.')
    print('6. subfolder <create|delete> path - Create or delete a subfolder on the server.')
    print('7. q                              - Quit.')

    while True:
        user_input = input('Enter command: ').strip()
        if user_input == 'q':
            print('Exiting.')
            break

        parts = user_input.split(maxsplit=2)
        if len(parts) == 0:
            continue

        command = parts[0].lower()

        if command == 'send' and len(parts) == 2:
            message = parts[1]
            send_message(message)

        elif command == 'sendfile' and len(parts) == 2:
            filepath = parts[1]
            send_file(filepath)

        elif command == 'getfile' and len(parts) == 2:
            filename = parts[1]
            get_file(filename)

        elif command == 'delete' and len(parts) == 2:
            filename = parts[1]
            delete_file(filename)

        elif command == 'dir':
            directory_listing()

        elif command == 'subfolder' and len(parts) == 3:
            action = parts[1]
            path = parts[2]
            if action.lower() in ('create', 'delete'):
                manage_subfolder(action, path)
            else:
                print('Invalid subfolder action. Use create or delete.')

        else:
            print('Invalid command or missing arguments.')
