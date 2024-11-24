import socket
import threading
import os
from time import perf_counter as pc
from network_analysis import NetworkMetrics
from tqdm import tqdm
import json

# Server Configuration
HOST = '10.128.0.2'  # Google Cloud VM internal IP address
PORT = 3300
BUFFER_SIZE = 4096
DASHES = '----> '

# Directory to save received files
RECEIVED_FILES_DIR = 'received_files'
os.makedirs(RECEIVED_FILES_DIR, exist_ok=True)

# Lock for file operations to prevent concurrent access issues
file_lock = threading.Lock()

# Counters file to keep track of saved files for file naming
json_file = 'file_counters.json'
def read_counters() :
    with open(json_file, 'r') as f :
        counters = json.load(f)
    return counters

# Updates the counter in the counters file
def update_counter(counter_name) :
    counters = read_counters()
    counters[counter_name] += 1
    with open(json_file, 'w') as f :
        json.dump(counters, f, indent=4)

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
                handle_send_file(connection, addr, message)
            elif message.startswith('GET_FILE'):
                handle_get_file(connection, addr, message)
            elif message.startswith('DELETE'):
                handle_delete_file(connection, addr, message)
            elif message.startswith('DIR'):
                handle_directory_listing(connection)
            elif message.startswith('SUBFOLDER'):
                handle_subfolder(connection, message)
            else:
                print(f'[*] Data received from {addr[0]}:{addr[1]}: {message}')
                response = DASHES + message
                connection.send(response.encode('utf-8'))

    except Exception as e:
        print(f'[!] Exception handling client {addr[0]}:{addr[1]}: {e}')
    finally:
        connection.close()

def handle_send_file(connection, addr, message):
    # Protocol: SEND_FILE filename size
    parts = message.split()
    if len(parts) != 3:
        connection.send('Invalid SEND_FILE command format.'.encode('utf-8'))
        return

    action, filename, filesize_str = parts
    try:
        filesize = int(filesize_str)
    except ValueError:
        connection.send('Invalid file size.'.encode('utf-8'))
        return
    
    connection.send('READY'.encode('utf-8'))
    
    # Get the filename and extension from the client
    c_filename = os.path.splitext(filename)[0]
    file_extension = os.path.splitext(filename)[1]
    s_filename=''
    # Cases for different file types to handle naming
    counters = read_counters()
    if file_extension == '.txt' :
        s_filename+='TS' + str(counters['txt'])
        update_counter('txt')
    elif file_extension == '.mp4' :
        s_filename+='VS' + str(counters['mp4'])
        update_counter('mp4')
    elif file_extension == '.wav' :
        s_filename+='AS' + str(counters['wav'])
        update_counter('wav')
    else :
        connection.send('Invalid file type.'.encode('utf-8'))
        return
    
    # Create where the received file will be saved
    file_path = os.path.join(RECEIVED_FILES_DIR, s_filename)
    
    # Receive the file data and show progress using the tqdm dependency
    tic = pc()
    progress_bar_r = tqdm(total=filesize, unit='B', unit_scale=True, desc=f'Receiving {c_filename}{file_extension}')
    file_data = b''
    # Receive packets in a loop based on the number of bytes allowed in the buffer
    while len(file_data) < filesize:
        packet = connection.recv(BUFFER_SIZE)
        if not packet:
            break
        file_data += packet
        progress_bar_r.update(len(packet))
    progress_bar_r.close()
    toc = pc()

    # Save the file
    with file_lock:
        with open(file_path, 'wb') as f:
            f.write(file_data)
    print(f'[*] Received file from {addr[0]}:{addr[1]} saved as {file_path}')
    connection.send(f'File {filename} received successfully.'.encode('utf-8'))

    # Calculating and printing the network metrics
    metrics = NetworkMetrics()
    time = round(toc - tic, 2)
    megabyte = 1000000
    speed = (filesize/megabyte) / time
    metrics.log_transfer(action, filename, filesize, time, speed)
    print('Network Metrics:')
    for metric in metrics.data_transfer_log[0] :
        print(f'{metric} : {metrics.data_transfer_log[0][metric]}')

def handle_get_file(connection, addr, message):
    # Protocol: GET_FILE filename
    parts = message.split()
    if len(parts) != 2:
        connection.send('Invalid GET_FILE command format.'.encode('utf-8'))
        return

    action, filename = parts
    file_path = os.path.join(RECEIVED_FILES_DIR, filename)
    if not os.path.exists(file_path):
        connection.send('ERROR: File does not exist.'.encode('utf-8'))
        return

    filesize = os.path.getsize(file_path)
    connection.send(f'FILE {filesize}'.encode('utf-8'))

    # Wait for the client to be ready
    ack = connection.recv(BUFFER_SIZE).decode('utf-8')
    if ack != 'READY':
        return

    # Send the file data with thread-safe operations
    tic = pc()
    with file_lock:
        progress_bar_s = tqdm(total=filesize, unit='B', unit_scale=True, desc=f'Sending {filename}')
        with open(file_path, 'rb') as f:
            while True:
                bytes_read = f.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                connection.sendall(bytes_read)
                progress_bar_s.update(len(bytes_read))
            progress_bar_s.close()
    toc = pc()

    print(f'[*] Sent file {filename} to {addr[0]}:{addr[1]}')

    # Calculating and printing the network metrics
    metrics = NetworkMetrics()
    time = round(toc - tic, 2)
    megabyte = 1000000
    speed = (filesize/megabyte) / time
    metrics.log_transfer(action, filename, filesize, time, speed)
    print('Network Metrics:')
    for metric in metrics.data_transfer_log[0] :
        print(f'{metric} : {metrics.data_transfer_log[0][metric]}')

def handle_delete_file(connection, addr, message):
    # Protocol: DELETE filename
    parts = message.split()
    if len(parts) != 2:
        connection.send('Invalid DELETE command format.'.encode('utf-8'))
        return

    _, filename = parts
    file_path = os.path.join(RECEIVED_FILES_DIR, filename)

    # Check if file is being processed
    if file_lock.locked():
        connection.send('ERROR: File is currently being processed.'.encode('utf-8'))
        return

    # Attempt to delete the file
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f'[*] File {filename} deleted by {addr[0]}:{addr[1]}')
            connection.send(f'File {filename} deleted successfully.'.encode('utf-8'))
        except Exception as e:
            print(f'[!] Error deleting file {filename}: {e}')
            connection.send(f'ERROR: Could not delete file {filename}.'.encode('utf-8'))
    else:
        connection.send('ERROR: File does not exist.'.encode('utf-8'))

def handle_directory_listing(connection):
    # List files and subdirectories in the RECEIVED_FILES_DIR
    try:
        entries = os.listdir(RECEIVED_FILES_DIR)
        if entries:
            listing = '\n'.join(entries)
        else:
            listing = 'The directory is empty.'
        connection.send(listing.encode('utf-8'))
    except Exception as e:
        print(f'[!] Error listing directory: {e}')
        connection.send('ERROR: Could not list directory.'.encode('utf-8'))

def handle_subfolder(connection, message):
    # Protocol: SUBFOLDER {CREATE|DELETE} path
    parts = message.split(maxsplit=2)
    if len(parts) != 3:
        connection.send('Invalid SUBFOLDER command format.'.encode('utf-8'))
        return

    _, action, subfolder_path = parts
    full_path = os.path.join(RECEIVED_FILES_DIR, subfolder_path)

    if action.upper() == 'CREATE':
        try:
            os.makedirs(full_path, exist_ok=False)
            print(f'[*] Subfolder {subfolder_path} created.')
            connection.send(f'Subfolder {subfolder_path} created successfully.'.encode('utf-8'))
        except FileExistsError:
            connection.send('ERROR: Subfolder already exists.'.encode('utf-8'))
        except Exception as e:
            print(f'[!] Error creating subfolder {subfolder_path}: {e}')
            connection.send(f'ERROR: Could not create subfolder {subfolder_path}.'.encode('utf-8'))
    elif action.upper() == 'DELETE':
        try:
            os.rmdir(full_path)
            print(f'[*] Subfolder {subfolder_path} deleted.')
            connection.send(f'Subfolder {subfolder_path} deleted successfully.'.encode('utf-8'))
        except FileNotFoundError:
            connection.send('ERROR: Subfolder does not exist.'.encode('utf-8'))
        except OSError as e:
            print(f'[!] Error deleting subfolder {subfolder_path}: {e}')
            connection.send(f'ERROR: Could not delete subfolder {subfolder_path}. It may not be empty.'.encode('utf-8'))
    else:
        connection.send('ERROR: Invalid SUBFOLDER action. Use CREATE or DELETE.'.encode('utf-8'))

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