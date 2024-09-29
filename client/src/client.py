import socket
import sys

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

def send_command(sock, command):
    sock.sendall((command + '\r\n').encode())
    response = sock.recv(BUFFER_SIZE).decode()
    print(response)
    return response

def main():
    ip_address, port_number = parse_arguments()

    # 创建TCP socket连接
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip_address, port_number))
        
        # 读取欢迎消息
        response = sock.recv(BUFFER_SIZE).decode()
        print(response)

        while True:
            command = input("Enter command: ")
            if command.lower() == 'quit':
                send_command(sock, 'QUIT')
                break
            
            # 解析和发送其他FTP命令
            if command.startswith("USER"):
                send_command(sock, command)
            elif command.startswith("PASS"):
                send_command(sock, command)
            elif command.startswith("RETR"):
                send_command(sock, command)
                # 处理文件接收逻辑
            elif command.startswith("STOR"):
                send_command(sock, command)
                # 处理文件发送逻辑
            elif command.startswith("LIST"):
                send_command(sock, command)
                # 处理目录列表逻辑
            # 添加其他命令处理...
            else:
                print("Command not recognized.")

if __name__ == "__main__":
    main()
