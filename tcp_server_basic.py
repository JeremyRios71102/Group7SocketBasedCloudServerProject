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