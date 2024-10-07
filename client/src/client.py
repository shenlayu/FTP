import socket
import sys
import random
import os

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 21
BUFFER_SIZE = 8192

def parse_arguments():
    ip_address = DEFAULT_IP
    port_number = DEFAULT_PORT

    for i in range(1, len(sys.argv)):
        if sys.argv[i] == '-ip' and i + 1 < len(sys.argv):
            ip_address = sys.argv[i + 1]
        elif sys.argv[i] == '-port' and i + 1 < len(sys.argv):
            port_number = int(sys.argv[i + 1])

    return ip_address, port_number

def send_command(sock: socket.socket, command):
    sock.sendall(command.encode())
    response = ''
    while True:
        # 从服务器接收数据
        part = sock.recv(BUFFER_SIZE).decode()
        response += part

        # 检查响应开头是否是三位状态码
        lines = response.splitlines()

        if len(lines) > 0:
            # 解析第一行
            last_line = lines[-1]
            
            # 如果是多行响应，状态码后会带有连字符 (e.g., "230-")
            if len(last_line) >= 4 and last_line[3] == '-':
                continue  # 继续接收响应

            # 检查状态码后是否是空格 (e.g., "230 ")
            if len(last_line) >= 4 and last_line[3] == ' ':
                break  # 单行响应或最后一行响应，退出循环

    # 打印并返回完整的响应信息
    print("RESPONSE:\n", response.strip())
    return last_line.strip()

def retrieve_file(sock: socket.socket, filename: str, data_ip_address, constructing_data_method: dict):
    local_save_path = input("Input the local path to save the downloaded file: ")
    response = send_command(sock, f"RETR {filename}")

    if response.startswith("550 "):
        return
    elif response.startswith("150 "):
        if constructing_data_method["method"] == "PORT":
            pass
        elif constructing_data_method["method"] == "PASV":
            data_ip_address = constructing_data_method["ip_address"]
            data_port_number = constructing_data_method["port_number"]

            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((data_ip_address, data_port_number))
            print("Data connection established.")
        else:
            print("Data connection must be established befoere transporting data.")
            return
        
        # TODO
        data_sock.close()
    else:
        pass

def store_file(sock: socket.socket, filename: str, constructing_data_method: dict):
    local_file_name = input("Input the local file to upload: ")
    response = send_command(sock, f"STOR {filename}")

    if response.startswith("550 "):
        return
    elif response.startswith("150 "):
        if constructing_data_method["method"] == "PORT":
            pass
        elif constructing_data_method["method"] == "PASV":
            data_ip_address = constructing_data_method["ip_address"]
            data_port_number = constructing_data_method["port_number"]

            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((data_ip_address, data_port_number))
            print("Data connection established.")
        else:
            print("Data connection must be established befoere transporting data.")
            return
        
        with open(local_file_name, 'rb') as f:
            while True:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                data_sock.sendall(data)
                print(f"Sent {len(data)} bytes")
            print(f"File {filename} stored successfully.")
        data_sock.close()
    else:
        pass

def create_data_socket(ip, port):
    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_sock.bind((ip, 0))  # Bind to a random port
    data_sock.listen(1)  # Listen for one connection
    return data_sock

def main():
    ip_address, port_number = parse_arguments()
    constructing_data_method = {
        "method": "nothing",
        "ip_address": "",
        "port_number": -1
    }

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
            if command.lower() == 'quit':
                send_command(sock, 'QUIT')
                break

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
                        constructing_data_method["method"] = "PORT"
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
                    # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_sock:
                    # data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    # data_sock.connect((data_ip_address, data_port_number))
                    # print("Data connection established.")
                    constructing_data_method["method"] = "PASV"
                    constructing_data_method["ip_address"] = data_ip_address
                    constructing_data_method["port_number"] = data_port_number

            elif command.startswith("RETR"):
                filename = command.split(' ')[1]
                retrieve_file(sock, filename, constructing_data_method)

            elif command.startswith("STOR"):
                filename = command.split(' ')[1]
                store_file(sock, filename, constructing_data_method)
                #     data_sock.close()
                #     constructed_data_connection = False
                # elif constructing_data_connection:
                #     pass
                # else:
                #     print("Data connection must be established befoere transporting data.")

            # 解析和发送其他FTP命令
            # response = send_command(sock, command)
            # if response.startswith("200"):  # 一般命令成功的返回码
            #     print("Command executed successfully.")
            # else:
            #     print("Command failed with response:", response)

if __name__ == "__main__":
    main()
