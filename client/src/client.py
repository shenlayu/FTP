import socket
import sys
from enum import Enum
import time
from pathlib import Path
import os

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 21
BUFFER_SIZE = 8192

class Method(Enum):
    NOTHING = 1
    PASV = 2
    PORT = 3

class Data_connection_method:
    def __init__(self):
        self.method: Method = Method.NOTHING
        self.ip_address: str = ""
        self.port_number: int = 0
        self.data_sock = 0

def parse_arguments():
    ip_address = DEFAULT_IP
    port_number = DEFAULT_PORT

    for i in range(1, len(sys.argv)):
        if sys.argv[i] == '-ip' and i + 1 < len(sys.argv):
            ip_address = sys.argv[i + 1]
        elif sys.argv[i] == '-port' and i + 1 < len(sys.argv):
            port_number = int(sys.argv[i + 1])

    return ip_address, port_number

def get_local_ip():
    try:
        # 创建一个临时 socket 连接到外部（即使不实际连接也能获取 IP）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"Error: {e}"

def send_command(sock: socket.socket, command):
    """
    向server发送一次请求并获得一次预期response.
    """
    message = command + "\r\n"
    sock.sendall(message.encode())
    return receive_response(sock)

def receive_response(sock: socket.socket):
    """
    从server获得一次预期response.
    """
    response = ''
    while True:
        part = sock.recv(BUFFER_SIZE).decode()
        response += part

        lines = response.splitlines()

        if len(lines) > 0:
            last_line = lines[-1]
            
            if len(last_line) >= 4 and last_line[3] == '-':
                continue
            if len(last_line) >= 4 and last_line[3] == ' ':
                break

    print(response.strip(), flush=True)
    return last_line.strip()

def get_base_path():
    if getattr(sys, '_MEIPASS', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent
    
def retrieve_file(sock: socket.socket, filename: str, data_connection_method: Data_connection_method):
    # current_directory = "/Users/qiaoshenyu/Desktop/大三上/计网/lhw1/ForStudents/autograde/autograde_client"
    current_directory = get_base_path().resolve()
    # current_directory = "/home/shenyu/projects/ftp/client"
    
    local_save_path = os.path.join(current_directory, filename)
    response = send_command(sock, f"RETR {filename}")

    if response.startswith("550 "):
        return False
    elif response.startswith("150 ") or response.startswith("125 "):
        if data_connection_method.method == Method.PORT:
            data_sock, addr = data_connection_method.data_sock.accept()
        elif data_connection_method.method == Method.PASV:
            data_ip_address = data_connection_method.ip_address
            data_port_number = data_connection_method.port_number

            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((data_ip_address, data_port_number))
        else:
            print("Data connection must be established befoere transporting data.")
            receive_response(sock)
            return False
        
        with open(local_save_path, 'wb') as f:
            while True:
                data = data_sock.recv(BUFFER_SIZE)
                if not data:
                    break
                f.write(data)
        
        data_sock.close()
        if data_connection_method == Method.PORT:
            data_connection_method.data_sock.close()

        response = receive_response(sock)
        if response.startswith("226 "):
            pass
        else:
            print("Something went wrong while storing.")

        return True
    else:
        pass

def store_file(sock: socket.socket, filename: str, data_connection_method: Data_connection_method) -> bool:
    if not os.path.isfile(filename):
        print(f"File '{filename}' does not exist.")
        return False

    base_filename = os.path.basename(filename)

    response = send_command(sock, f"STOR {base_filename}")

    if response.startswith("451 "):
        return False
    elif response.startswith("150 "):
        if data_connection_method.method == Method.PORT:
            data_sock, addr = data_connection_method.data_sock.accept()
        elif data_connection_method.method == Method.PASV:
            data_ip_address = data_connection_method.ip_address
            data_port_number = data_connection_method.port_number

            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((data_ip_address, data_port_number))
        else:
            print("Data connection must be established befoere transporting data.")
            receive_response(sock)
            return False
        
        with open(filename, 'rb') as f:
            while True:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                data_sock.sendall(data)
        
        data_sock.close()
        if data_connection_method.method == Method.PORT:
            data_connection_method.data_sock.close()
        
        response = receive_response(sock)
        if response.startswith("226 "):
            pass
        else:
            print("Something went wrong while storing.")
        
        return True
    else:
        pass

def create_data_socket(ip, port):
    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_sock.bind((ip, 0))  # Bind to a random port
    data_sock.listen(1)  # Listen for one connection
    return data_sock

def list_files(sock: socket.socket, data_connection_method: Data_connection_method):
    response = send_command(sock, "LIST")
    if response.startswith("150 "):
        if data_connection_method.method == Method.PORT:
            data_sock, addr = data_connection_method.data_sock.accept()
            print("Data connection established.")
        elif data_connection_method.method == Method.PASV:
            data_ip_address = data_connection_method.ip_address
            data_port_number = data_connection_method.port_number

            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((data_ip_address, data_port_number))
            print("Data connection established.")
        else:
            print("Data connection must be established before retrieving the file list.")
            receive_response(sock)
            return False
        
        file_list = ''
        while True:
            data = data_sock.recv(BUFFER_SIZE).decode()
            if not data:
                break
            file_list += data

        print(file_list)
        data_sock.close()
        if data_connection_method.method == Method.PORT:
            data_connection_method.data_sock.close()

        response = receive_response(sock)
        if response.startswith("226 "):
            print("File list retrieved successfully.")
        else:
            print("Something went wrong while retrieving the file list.")

        return True
    else:
        print("Failed to retrieve file list.")
        return False

def change_directory(sock: socket.socket, directory: str):
    response = send_command(sock, f"CWD {directory}")
    
    if response.startswith("250 "):
        pass
    else:
        print(f"Failed to change directory to {directory}: {response}")

def print_working_directory(sock: socket.socket):
    response = send_command(sock, "PWD")
    if response.startswith("257 "):
        pass
    else:
        print(f"Failed to get working directory: {response}")

def make_directory(sock: socket.socket, directory: str):
    response = send_command(sock, f"MKD {directory}")
    if response.startswith("257 "):
        pass
    else:
        print(f"Failed to create directory {directory}: {response}")

def remove_directory(sock: socket.socket, directory: str):
    response = send_command(sock, f"RMD {directory}")
    if response.startswith("250 "):
        pass
    else:
        print(f"Failed to remove directory {directory}: {response}")

def main():
    ip_address, port_number = parse_arguments()
    data_connection_method = Data_connection_method()

    # 创建TCP socket连接
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip_address, port_number))
        
        # 读取欢迎消息
        response = sock.recv(BUFFER_SIZE).decode()
        time.sleep(0.1)
        print(response, flush=True)

        logged_in = False
        # 登录逻辑
        while not logged_in:
            user_command = input()
            if user_command.startswith("USER"):
                response = send_command(sock, user_command)
                
                if response.startswith("331 "):  # 331 表示需要密码
                    email_command = input()

                    if email_command.startswith("PASS "):
                        response = send_command(sock, email_command)
                        
                        if response.startswith("230 "):  # 230 表示登录成功
                            logged_in = True
                        else:
                            print("Login failed. Please try again.")
                    elif email_command == 'QUIT' or email_command == 'ABOR':
                        send_command(sock, 'QUIT')
                        sock.close()
                        break
                    else:
                        print("Invalid command. Please enter PASS command.")
                else:
                    print("Invalid username. Please try again.")
            elif user_command == 'QUIT' or user_command == 'ABOR':
                send_command(sock, 'QUIT')
                sock.close()
                break
            else:
                print("Invalid command. Please enter USER command first.")

        while logged_in:
            command = input()
            if command.startswith("PORT"):
                if len(command.split(' ')) != 2:
                    print("Amount of argument should be 1.")
                    continue
                ip_port = command.split(' ')[1]
                try:
                    ip_address, port_number_1, port_number_2 = ip_port.split(','[:4]), ip_port.split(',')[4], ip_port.split(',')[5]
                    port_number_1 = int(port_number_1)
                    port_number_2 = int(port_number_2)

                    # 检查端口号是否在有效范围内
                    if 0 <= 256 * port_number_1 + port_number_2 <= 65535:
                        data_connection_method.method = Method.PORT
                        data_connection_method.ip_address = f"{ip_address[0]}.{ip_address[1]}.{ip_address[2]}.{ip_address[3]}"
                        data_connection_method.port_number = 256 * port_number_1 + port_number_2

                        port_command = f"PORT {ip_port}"
                        data_connection_method.data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        try:
                            data_connection_method.data_sock.bind((data_connection_method.ip_address, data_connection_method.port_number))
                        except socket.error as e:
                            print(f"Failed to bind to {data_connection_method.ip_address}: \
                                  {data_connection_method.port_number} - {e}", file=sys.stderr, flush=True)
                            continue
                        data_connection_method.data_sock.listen(1)

                        response = send_command(sock, port_command)
                    else:
                        print("Invalid port number. Please enter a port number between 20000 and 65535.")
                except ValueError:
                    print("Invalid input format. Please enter in the format IP:PORT (e.g., 127.0.0.1:8888).")

            elif command.startswith("PASV"):
                response = send_command(sock, "PASV")

                # 解析服务器返回的IP和端口
                if response.startswith("227 "):
                    parts = response.split('(')[1].split(')')[0].split(',')
                    data_ip_address = '.'.join(parts[:4])
                    data_port_number = int(parts[4]) * 256 + int(parts[5])

                    # 创建数据连接
                    data_connection_method.method = Method.PASV
                    data_connection_method.ip_address = data_ip_address
                    data_connection_method.port_number = data_port_number

            elif command.startswith("RETR"):
                if len(command.split(' ')) != 2:
                    print("Amount of argument should be 1.")
                    continue
                filename = command.split(' ')[1]
                if retrieve_file(sock, filename, data_connection_method):
                    data_connection_method.method = Method.NOTHING

            elif command.startswith("STOR"):
                if len(command.split(' ')) != 2:
                    print("Amount of argument should be 1.")
                    continue
                filename = command.split(' ')[1]
                if store_file(sock, filename, data_connection_method):
                    data_connection_method.method = Method.NOTHING

            elif command == "SYST":
                send_command(sock, "SYST")

            elif command.startswith("TYPE"):
                send_command(sock, command)

            elif command.startswith("LIST"):
                if list_files(sock, data_connection_method):
                    data_connection_method.method = Method.NOTHING

            elif command.startswith("CWD"):
                if len(command.split(' ')) != 2:
                    print("Amount of argument should be 1.")
                    continue
                directory = command.split(' ')[1]
                change_directory(sock, directory)

            elif command.startswith("PWD"):
                print_working_directory(sock)

            elif command.startswith("MKD"):
                if len(command.split(' ')) != 2:
                    print("Amount of argument should be 1.")
                    continue
                directory = command.split(' ')[1]
                make_directory(sock, directory)

            elif command.startswith("RMD"):
                if len(command.split(' ')) != 2:
                    print("Amount of argument should be 1.")
                    continue
                directory = command.split(' ')[1]
                remove_directory(sock, directory)

            elif command == 'QUIT' or command == 'ABOR':
                send_command(sock, 'QUIT')
                sock.close()
                break

if __name__ == "__main__":
    main()