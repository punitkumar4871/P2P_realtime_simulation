import socket
import threading
import tqdm
import os
import argparse

BUFFER_SIZE = 4096
SEPARATOR = "<SEPARATOR>"

def handle_send(peer_socket, filename):
    try:
        # Verify file exists and get its size
        if not os.path.exists(filename):
            print(f"[!] File '{filename}' does not exist.")
            return

        filesize = os.path.getsize(filename)
        peer_socket.send(f"{filename}{SEPARATOR}{filesize}".encode())
        print(f"[+] Sending file {filename} of size {filesize} bytes.")

        # Progress bar
        progress = tqdm.tqdm(range(filesize), f"Sending {filename}", unit="B", unit_scale=True, unit_divisor=1024)

        # Send the file in chunks
        with open(filename, "rb") as f:
            while True:
                bytes_read = f.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                peer_socket.sendall(bytes_read)
                progress.update(len(bytes_read))
        
        print(f"[+] File {filename} sent successfully.")
    except Exception as e:
        print(f"[!] Error during sending: {e}")
    finally:
        peer_socket.close()


def handle_receive(peer_socket, target_directory):
    try:
        # Receive the file metadata (name and size)
        received = peer_socket.recv(BUFFER_SIZE).decode()
        filename, filesize = received.split(SEPARATOR)
        filename = os.path.basename(filename)
        filesize = int(filesize)

        # Determine the full path to save the file in the target directory
        target_path = os.path.join(target_directory, filename)

        print(f"[+] Receiving file {filename} of size {filesize} bytes.")
        
        if filesize == 0:
            print("[!] Received file has 0 bytes. Check if the sending peer has a valid file.")
            return

        # Progress bar
        progress = tqdm.tqdm(range(filesize), f"Receiving {filename}", unit="B", unit_scale=True, unit_divisor=1024)

        # Open file for writing in binary mode
        with open(target_path, "wb") as f:
            total_received = 0
            while total_received < filesize:
                bytes_read = peer_socket.recv(BUFFER_SIZE)
                if not bytes_read:
                    print("[!] Connection closed unexpectedly.")
                    break
                f.write(bytes_read)
                total_received += len(bytes_read)
                progress.update(len(bytes_read))
        
        print(f"[+] File {filename} received successfully with {total_received} bytes.")
    except Exception as e:
        print(f"[!] Error during receiving: {e}")
    finally:
        peer_socket.close()


def peer(host, port, action, filename=None, target_directory="."):
    if action == 'receive':
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
            peer_socket.bind((host, port))
            peer_socket.listen(1)
            print(f"[*] Listening for incoming connections on {host}:{port}")
            while True:
                conn, addr = peer_socket.accept()
                print(f"[+] Connection from {addr}")
                threading.Thread(target=handle_receive, args=(conn, target_directory)).start()
    elif action == 'send':
        peer_ip = input("Enter peer IP address to connect to: ").strip()
        peer_port = input("Enter peer port number: ").strip()
        
        if not peer_ip or not peer_port:
            print("[!] IP address and port number are required.")
            return

        try:
            peer_port = int(peer_port)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
                peer_socket.connect((peer_ip, peer_port))
                print("[+] Connected.")
                handle_send(peer_socket, filename)
        except ValueError:
            print("[!] Invalid port number.")
        except ConnectionRefusedError:
            print("[!] Connection refused. Make sure the peer is listening and the IP/port are correct.")
        except Exception as e:
            print(f"[!] An error occurred: {e}")

def start_receiver(host, port, target_directory):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"[*] Listening for incoming connections on {host}:{port}")
        while True:
            conn, addr = server_socket.accept()
            print(f"[+] Connection from {addr}")
            threading.Thread(target=handle_receive, args=(conn, target_directory)).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='P2P File Transfer')
    parser.add_argument('action', choices=['send', 'receive'], help='Action to perform')
    parser.add_argument('--filename', type=str, help='File to send (only needed for send action)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5001, help='Port to bind (default: 5001)')
    parser.add_argument('--target-directory', type=str, default='.', help='Directory to save received files (only needed for receive action)')
    
    args = parser.parse_args()
    
    if args.action == 'send' and not args.filename:
        print("Filename must be specified for sending.")
    else:
        peer(args.host, args.port, args.action, args.filename, args.target_directory)
