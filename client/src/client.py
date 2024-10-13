import socket
import sys
from enum import Enum

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 21
BUFFER_SIZE = 8192

# TODO 如果没PASV或PORT要报错
# TODO 连服务器，测试大文件传输
# TODO 纠错
# TODO 选做，图形化界面
# TODO 选做，断线重连
# TODO 传输文件开启新线程
# TODO 少几个命令

class Method(Enum):
    NOTHING = 1
    PASV = 2
    PORT = 3

class Data_connection_method:
    def __init__(self):
        self.method: Method = Method.NOTHING
        self.ip_address: str = ""
        self.port_number: int = 0

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
    sock.sendall(command.encode())
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

    print("RESPONSE:\n", response.strip())
    return last_line.strip()

def retrieve_file(sock: socket.socket, filename: str, data_connection_method: Data_connection_method):
    local_save_path = input("Input the local path to save the downloaded file: ")
    response = send_command(sock, f"RETR {filename}")

    if response.startswith("550 "):
        return False
    elif response.startswith("150 "):
        if data_connection_method.method == Method.PORT:
            data_ip_address = data_connection_method.ip_address
            data_port_number = data_connection_method.port_number

            data_sock_listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            data_sock_listen.bind((data_ip_address, data_port_number))
            data_sock_listen.listen(1)

            data_sock, addr = data_sock_listen.accept()
            print("Data connection established.")
        elif data_connection_method.method == Method.PASV:
            data_ip_address = data_connection_method.ip_address
            data_port_number = data_connection_method.port_number

            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((data_ip_address, data_port_number))
            print("Data connection established.")
        else:
            print("Data connection must be established befoere transporting data.")
            return False
        
        with open(local_save_path, 'wb') as f:
            while True:
                data = data_sock.recv(BUFFER_SIZE)
                if not data:
                    break
                f.write(data)
                print(f"Received {len(data)} bytes")
        
        data_sock.close()
        if data_connection_method == Method.PORT:
            data_sock_listen.close()

        response = receive_response(sock)
        if response.startswith("226 "):
            print(f"File {filename} retrieved successfully.")
        else:
            print("Something went wrong while storing.")

        return True
    else:
        pass

def store_file(sock: socket.socket, filename: str, data_connection_method: Data_connection_method):
    local_file_name = input("Input the local file to upload: ")
    response = send_command(sock, f"STOR {filename}")

    if response.startswith("550 "):
        return False
    elif response.startswith("150 "):
        if data_connection_method.method == Method.PORT:
            data_ip_address = data_connection_method.ip_address
            data_port_number = data_connection_method.port_number

            data_sock_listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            data_sock_listen.bind((data_ip_address, data_port_number))
            data_sock_listen.listen(1)

            data_sock, addr = data_sock_listen.accept()
            print("Data connection established.")
        elif data_connection_method.method == Method.PASV:
            data_ip_address = data_connection_method.ip_address
            data_port_number = data_connection_method.port_number

            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((data_ip_address, data_port_number))
            print("Data connection established.")
        else:
            print("Data connection must be established befoere transporting data.")
            return False
        
        with open(local_file_name, 'rb') as f:
            while True:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                data_sock.sendall(data)
                print(f"Sent {len(data)} bytes")
        
        data_sock.close()
        if data_connection_method.method == Method.PORT:
            data_sock_listen.close()
        
        response = receive_response(sock)
        if response.startswith("226 "):
            print(f"File {filename} stored successfully.")
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
    print(response + "\n\naaa")
    if response.startswith("150 "):
        if data_connection_method.method == Method.PORT:
            data_ip_address = data_connection_method.ip_address
            data_port_number = data_connection_method.port_number

            data_sock_listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            data_sock_listen.bind((data_ip_address, data_port_number))
            data_sock_listen.listen(1)

            data_sock, addr = data_sock_listen.accept()
            print("Data connection established.")
        elif data_connection_method.method == Method.PASV:
            data_ip_address = data_connection_method.ip_address
            data_port_number = data_connection_method.port_number

            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("whywhy\n\nwhywhy")
            data_sock.connect((data_ip_address, data_port_number))
            print("Data connection established.")
        else:
            print("Data connection must be established before retrieving the file list.")
            return False
        
        print("Receiving file list:")
        file_list = ''
        while True:
            data = data_sock.recv(BUFFER_SIZE).decode()
            if not data:
                break
            file_list += data

        print(file_list)
        data_sock.close()
        if data_connection_method.method == Method.PORT:
            data_sock_listen.close()

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
        print(f"Changed directory to {directory}")
    else:
        print(f"Failed to change directory to {directory}: {response}")

def print_working_directory(sock: socket.socket):
    response = send_command(sock, "PWD")
    if response.startswith("257 "):
        print(f"Current directory: {response}")
    else:
        print(f"Failed to get working directory: {response}")

def make_directory(sock: socket.socket, directory: str):
    response = send_command(sock, f"MKD {directory}")
    if response.startswith("257 "):
        print(f"Directory {directory} created successfully.")
    else:
        print(f"Failed to create directory {directory}: {response}")

def remove_directory(sock: socket.socket, directory: str):
    response = send_command(sock, f"RMD {directory}")
    if response.startswith("250 "):
        print(f"Directory {directory} removed successfully.")
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
        print("RESPONSE:\n", response)

        logged_in = False
        # 登录逻辑
        while not logged_in:
            user_command = input("Enter USER command (e.g., USER anonymous): ")
            if user_command.startswith("USER"):
                response = send_command(sock, user_command)
                
                # 使用返回码判断是否需要输入密码
                if response.startswith("331 "):  # 331 表示需要密码
                    email = input("Enter your email as password (e.g., PASS your_email@example.com): ")
                    response = send_command(sock, f'PASS {email}')
                    
                    # 使用返回码判断登录是否成功
                    if response.startswith("230 "):  # 230 表示登录成功
                        print("Login successful.")
                        logged_in = True
                    else:
                        print("Login failed. Please try again.")
                else:
                    print("Invalid username. Please try again.")
            else:
                print("Invalid command. Please enter USER command first.")

        while logged_in:
            command = input("Enter command: ")
            if command.startswith("PORT"):
                # 用户以 "127.0.0.1:8888" 格式提供IP和端口
                ip_port = input("Enter your IP address and port (e.g., 127.0.0.1:8888): ")
                try:
                    ip_address, port_number = ip_port.split(':')
                    port_number = int(port_number)

                    # 检查端口号是否在有效范围内
                    if 0 <= port_number <= 65535:
                        ip_parts = ip_address.split('.')
                        port1 = port_number // 256
                        port2 = port_number % 256
                        port_command = f"PORT {','.join(ip_parts)},{port1},{port2}"
                        response = send_command(sock, port_command)

                        data_connection_method.method = Method.PORT
                        data_connection_method.ip_address = ip_address
                        data_connection_method.port_number = port_number
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
                    print(f"Server IP: {data_ip_address}, Port: {data_port_number}")

                    # 创建数据连接
                    data_connection_method.method = Method.PASV
                    data_connection_method.ip_address = data_ip_address
                    data_connection_method.port_number = data_port_number

            elif command.startswith("RETR"):
                filename = command.split(' ')[1]
                if retrieve_file(sock, filename, data_connection_method):
                    data_connection_method.method = Method.NOTHING

            elif command.startswith("STOR"):
                filename = command.split(' ')[1]
                if store_file(sock, filename, data_connection_method):
                    data_connection_method.method = Method.NOTHING

            elif command == "SYST":
                send_command(sock, "SYST")

            elif command.startswith("TYPE"):
                type_code = input("Enter transfer type (A for ASCII, I for binary): ").strip().upper()
                send_command(sock, f"TYPE {type_code}")

            elif command.startswith("LIST"):
                if list_files(sock, data_connection_method):
                    data_connection_method.method = Method.NOTHING

            elif command.startswith("CWD"):
                directory = command.split(' ')[1]
                change_directory(sock, directory)

            elif command.startswith("PWD"):
                print_working_directory(sock)

            elif command.startswith("MKD"):
                directory = command.split(' ')[1]
                make_directory(sock, directory)

            elif command.startswith("RMD"):
                directory = command.split(' ')[1]
                remove_directory(sock, directory)

            if command == 'QUIT' or command == 'ABOR':
                send_command(sock, 'QUIT')
                sock.close()
                break

if __name__ == "__main__":
    main()
