import sys
import os
import socket
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, \
                             QPushButton, QLineEdit, QLabel, QMessageBox, QListWidgetItem, QInputDialog)
from PyQt5.QtGui import QColor, QFont, QIcon
from enum import Enum
import random

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

    print("RESPONSE:\n", response.strip())
    return last_line.strip()

class LoginWindow(QWidget):
    def __init__(self, server_ip, server_port):
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = None
        self.setWindowTitle('Login - Enter USER')
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        # 创建输入框和按钮
        self.user_input = QLineEdit(self)
        self.user_input.setPlaceholderText("Waiting for server response...")
        self.user_input.setEnabled(False)  # 禁用输入框，直到收到服务器的220响应
        layout.addWidget(self.user_input)

        self.login_button = QPushButton('Next', self)
        self.login_button.setEnabled(False)  # 同样禁用按钮
        self.login_button.clicked.connect(self.check_user_input)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

        # 启动连接服务器
        self.connect_to_server()

    def connect_to_server(self):
        """连接FTP服务器并等待220响应"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.server_ip, self.server_port))
            response = self.sock.recv(BUFFER_SIZE).decode()
            print("Server Response:\n", response)

            # 如果响应以"220 "开头，启用USER输入框
            if response.startswith("220 "):
                self.user_input.setEnabled(True)
                self.user_input.setPlaceholderText("Enter USER")
                self.login_button.setEnabled(True)
            else:
                self.show_error_message("Unexpected server response!")
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.show_error_message("无法连接到FTP服务器")

    def check_user_input(self):
        """检查USER输入并进入Email输入窗口"""
        user = self.user_input.text()
        if not user:
            self.show_error_message("USER cannot be empty!")
        else:
            # 发送USER命令到服务器
            self.user = user
            command = f"USER {user}"
            response = send_command(self.sock, command)

            # 检查是否成功
            if response.startswith("331 "):
                self.switch_to_email_window()
            else:
                self.show_error_message("找不到USER，请重试")

    def show_error_message(self, message):
        """显示错误提示框"""
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText(message)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()

    def switch_to_email_window(self):
        """切换到邮箱输入界面"""
        self.email_window = EmailWindow(self.user, self.sock)
        self.email_window.show()
        self.close()

class EmailWindow(QWidget):
    def __init__(self, user, sock):
        super().__init__()
        self.user = user
        self.sock = sock
        self.setWindowTitle('Login - Enter Email')
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        # 创建输入框和按钮
        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("Enter Email")
        layout.addWidget(self.email_input)

        self.submit_button = QPushButton('Submit', self)
        self.submit_button.clicked.connect(self.check_email_input)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def check_email_input(self):
        """检查邮箱输入并尝试登录"""
        email = self.email_input.text()
        self.email = email

        # 发送PASS命令到服务器
        command = f"PASS {email}"
        response = send_command(self.sock, command)

        # 检查是否成功
        if response.startswith("230 "):
            self.switch_to_main_window()
        else:
            self.show_error_message("Email输入无效，请重新输入USER")
            self.switch_to_user_window()

    def switch_to_user_window(self):
        """返回USER输入界面"""
        self.login_window = LoginWindow(self.server_ip, self.server_port)
        self.login_window.show()
        self.close()

    def switch_to_main_window(self):
        """切换到主界面"""
        self.main_window = FTPClientGUI(self.user, self.email, self.sock)
        self.main_window.show()
        self.close()

    def show_error_message(self, message):
        """显示错误提示框"""
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText(message)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()

class FTPClientGUI(QWidget):
    def __init__(self, user, email, sock):
        super().__init__()
        self.user = user
        self.email = email
        self.sock = sock
        self.data_connection_method = Data_connection_method()

        self.setWindowTitle('FTP Client')
        self.setGeometry(100, 100, 800, 600)

        main_layout = QVBoxLayout()

        # 用户信息和按钮行布局
        user_info_layout = QHBoxLayout()

        # 显示用户和邮箱信息
        self.user_label = QLabel(f"User: {self.user}")
        self.email_label = QLabel(f"Email: {self.email}")
        user_info_layout.addWidget(self.user_label)
        user_info_layout.addWidget(self.email_label)

        # 当前连接方式显示标签
        self.connection_mode_label = QLabel("当前连接方式: PASV")
        user_info_layout.addWidget(self.connection_mode_label)

        # 添加PASV和PORT按钮
        pasv_button = QPushButton('PASV')
        pasv_button.clicked.connect(self.set_pasv_mode)  # 连接到弹出窗口的函数
        user_info_layout.addWidget(pasv_button)

        port_button = QPushButton('PORT')
        port_button.clicked.connect(self.prompt_port_input)  # 暂时设置为Port模式
        user_info_layout.addWidget(port_button)

        main_layout.addLayout(user_info_layout)  # 将用户信息布局添加到主布局中

        # 创建第二行按钮布局 (存储按钮和退出按钮)
        mid_button_layout = QHBoxLayout()

        # 存储按钮
        stor_button = QPushButton('存储')
        stor_button.clicked.connect(self.handle_stor)  # 连接 STOR 功能
        mid_button_layout.addWidget(stor_button)

        # 取回按钮
        retr_button = QPushButton('取回')
        retr_button.clicked.connect(self.handle_retr)  # 连接 RETR 功能
        mid_button_layout.addWidget(retr_button)

        # 退出按钮
        quit_button = QPushButton('退出')
        quit_button.clicked.connect(self.handle_quit)  # 连接退出功能
        mid_button_layout.addWidget(quit_button)

        main_layout.addLayout(mid_button_layout)

        # 创建路径输入框
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText('Enter local path...')
        self.path_input.returnPressed.connect(self.navigate_to_input_path)
        main_layout.addWidget(self.path_input)

        # 创建中心文件列表布局（水平布局）
        file_list_layout = QHBoxLayout()

        # 本地文件列表
        self.local_list = QListWidget()
        self.local_list.itemDoubleClicked.connect(self.navigate_local_directory)
        file_list_layout.addWidget(self.local_list)

        # 服务器文件列表
        self.server_list = QListWidget()
        self.server_list.itemDoubleClicked.connect(self.navigate_server_directory)  # 绑定双击事件
        file_list_layout.addWidget(self.server_list)

        main_layout.addLayout(file_list_layout)

        # 创建底部按钮行（下方按钮）
        bottom_button_layout = QHBoxLayout()

        # 刷新按钮
        refresh_button = QPushButton('刷新')
        refresh_button.clicked.connect(self.handle_refresh)  # 连接刷新功能
        bottom_button_layout.addWidget(refresh_button)

        pwd_button = QPushButton('路径')
        pwd_button.clicked.connect(self.handle_pwd)  # 连接按钮点击事件
        bottom_button_layout.addWidget(pwd_button)

        new_folder_button = QPushButton('新建')  # 新建文件夹按钮
        new_folder_button.clicked.connect(self.create_new_directory)  # 连接按钮点击事件
        bottom_button_layout.addWidget(new_folder_button)

        delete_folder_button = QPushButton('删除')  # 删除文件夹按钮
        delete_folder_button.clicked.connect(self.delete_directory)  # 连接按钮点击事件
        bottom_button_layout.addWidget(delete_folder_button)

        main_layout.addLayout(bottom_button_layout)

        # 设置布局
        self.setLayout(main_layout)

        # 初始显示本地文件列表
        self.current_local_dir = os.path.expanduser('~')  # 默认到用户主目录
        self.update_local_file_list()

        self.update_server_file_list()

    def update_local_file_list(self):
        """更新本地文件列表显示，并按字典序排列"""
        self.local_list.clear()
        self.path_input.setText(self.current_local_dir)  # 更新路径输入框中的当前路径
        try:
            items = os.listdir(self.current_local_dir)
            items = sorted(items, key=str.lower)  # 使用字典序排序，忽略大小写
            self.local_list.addItem('..')  # 返回上一级目录的选项
            for item in items:
                full_path = os.path.join(self.current_local_dir, item)
                list_item = QListWidgetItem(item)
                if os.path.isdir(full_path):  # 如果是文件夹
                    list_item.setForeground(QColor("blue"))  # 设置文件夹颜色为蓝色
                    list_item.setFont(QFont('Arial', 13, QFont.Bold))  # 文件夹加粗显示
                else:
                    list_item.setForeground(QColor("black"))  # 文件颜色为黑色
                self.local_list.addItem(list_item)
        except Exception as e:
            print(f"无法访问目录: {e}")

    def navigate_local_directory(self, item):
        """处理本地文件列表中的双击事件"""
        selected_item = item.text()
        if selected_item == '..':  # 返回上一级
            self.current_local_dir = os.path.dirname(self.current_local_dir)
        else:
            selected_path = os.path.join(self.current_local_dir, selected_item)
            if os.path.isdir(selected_path):
                self.current_local_dir = selected_path
        self.update_local_file_list()

    def navigate_to_input_path(self):
        """处理输入框中的路径导航"""
        input_path = self.path_input.text()
        if os.path.isdir(input_path):
            self.current_local_dir = input_path
            self.update_local_file_list()
        else:
            self.show_error_message(f"Path '{input_path}' does not exist!")

    def return_to_user_input(self):
        """返回USER和PASS输入窗口"""
        QMessageBox.warning(self, "Error", "File list retrieval failed. Returning to login.")
        self.close()  # 关闭当前窗口
        self.show_login_window()  # 重新显示登录窗口

    def show_login_window(self):
        """显示登录窗口"""
        self.login_window = LoginWindow()  # 这里你需要有一个LoginWindow类
        self.login_window.show()

    def update_server_file_list(self):
        """更新服务器文件列表"""
        # 发送PASV命令获取数据连接
        try:
            if self.handle_pasv():
                # 获取服务器文件列表并更新界面
                self.list_files()
            else:
                raise Exception("Failed to retrieve the file list.")
        except Exception as e:
            print(f"Error: {e}")
            self.show_error_message(str(e))
            return False

    def handle_pasv(self):
        """处理PASV指令"""
        try:
            response = send_command(self.sock, "PASV")
            if response.startswith("227 "):
                parts = response.split('(')[1].split(')')[0].split(',')
                data_ip_address = '.'.join(parts[:4])
                data_port_number = int(parts[4]) * 256 + int(parts[5])
                print(f"Server IP: {data_ip_address}, Port: {data_port_number}")

                # 创建数据连接
                self.data_connection_method.method = Method.PASV
                self.data_connection_method.ip_address = data_ip_address
                self.data_connection_method.port_number = data_port_number

                return True
            else:
                return False
        except Exception as e:
            print(f"Error: {e}")
            return False
        
    def handle_port(self):
        """处理 PORT 模式的设置，并发送 PORT 命令"""
        try:
            # 计算 PORT 命令参数
            ip_parts = self.data_connection_method.ip_address.split('.')
            p1 = self.data_connection_method.port_number // 256
            p2 = self.data_connection_method.port_number % 256
            port_command = f"PORT {','.join(ip_parts)},{p1},{p2}"

            # 发送 PORT 命令到服务器
            response = send_command(self.sock, port_command)
            if response.startswith("200 "):
                print(f"PORT 模式设置成功，IP: {self.data_connection_method.port_number}, 端口: {self.data_connection_method.port_number}")
                return True
            else:
                self.show_error_message(f"PORT 模式设置失败: {response}")
                return False
        except Exception as e:
            self.show_error_message(f"PORT 模式设置出错: {e}")
            return False

    def set_pasv_mode(self):
        """弹出窗口显示PASV模式的设置结果并更新连接方式显示"""
        self.show_info_message("PASV模式设置成功")
        self.data_connection_method.method = Method.PASV
        self.update_connection_mode_display("PASV")

    def set_port_mode(self, port):
        """设置为PORT模式并更新显示"""
        self.data_connection_method.method = Method.PORT
        self.data_connection_method.ip_address = "127.0.0.1"  # 设置为本地回环地址
        self.data_connection_method.port_number = port
        self.show_info_message(f"PORT模式设置成功，端口: {port}")
        self.update_connection_mode_display("PORT")

    def prompt_port_input(self):
        """弹出选项框，提供手动输入端口和随机生成端口的选项"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("选择端口")
        msg_box.setText("请选择操作方式")
        
        manual_button = msg_box.addButton("手动输入端口", QMessageBox.ActionRole)
        random_button = msg_box.addButton("随机生成端口", QMessageBox.ActionRole)
        msg_box.addButton(QMessageBox.Cancel)
        
        msg_box.exec_()

        if msg_box.clickedButton() == manual_button:
            self.manual_port_input()
        elif msg_box.clickedButton() == random_button:
            self.set_random_port()

    def manual_port_input(self):
        """手动输入端口，并进行合法性检查"""
        while True:
            port_text, ok = QInputDialog.getText(self, '设置PORT', '请输入一个有效的端口(20001~65535):')
            if not ok:
                return  # 用户取消输入
            try:
                port = int(port_text)
                if 0 <= port <= 65535 and self.is_port_available(port):
                    self.set_port_mode(port)
                    break
                else:
                    self.show_error_message("输入的端口无效或已被占用，请重新输入")
            except ValueError:
                self.show_error_message("请输入有效的数字端口")

    def set_random_port(self):
        """随机生成一个未被占用的端口"""
        port = self.get_random_unused_port()
        if port:
            self.set_port_mode(port)
        else:
            self.show_error_message("未能找到可用端口，请重试")

    def get_random_unused_port(self):
        """生成一个未被占用的随机端口"""
        while True:
            port = random.randint(20001, 65535)  # 生成1024到65535范围内的随机端口
            if self.is_port_available(port):
                return port

    def is_port_available(self, port):
        """检查端口是否可用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) != 0  # 如果返回0，说明端口已被占用

    def is_port_available(self, port):
        """检查端口是否可用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) != 0  # 如果返回0，说明端口已被占用

    def update_connection_mode_display(self, mode):
        """更新界面上的连接方式显示"""
        if mode == "PORT":
            self.connection_mode_label.setText(f"当前连接方式: {mode} (端口: {self.data_connection_method.port_number})")
        else:
            self.connection_mode_label.setText(f"当前连接方式: {mode}")

    def handle_stor(self):
        """处理STOR按钮点击事件，用于将本地文件存储到服务器"""
        # 检查是否选中了文件
        selected_item = self.local_list.currentItem()
        if selected_item is None:
            self.show_error_message("未选择任何文件。请先选择一个文件。")
            return
        
        local_file_name = selected_item.text()
        local_file_path = os.path.join(self.current_local_dir, local_file_name)

        # 检查当前选择是否为文件
        if not os.path.isfile(local_file_path):
            self.show_error_message(f"{local_file_name} 不是一个有效的文件.")
            return
        
        # 弹出输入框，获取目标文件名
        server_file_name, ok = QInputDialog.getText(self, 'STOR', '请输入要存储的文件名:')
        
        if ok and server_file_name:
            # 发送PASV或PORT命令
            if self.data_connection_method.method == Method.PASV:
                if not self.handle_pasv():
                    self.show_error_message("PASV 模式设置失败.")
                    return
            elif self.data_connection_method.method == Method.PORT:
                if not self.handle_port():
                    self.show_error_message("PORT 模式设置失败.")
                    return

            # 发送STOR命令并开始文件传输
            self.store_file(self.sock, server_file_name, local_file_path, self.data_connection_method)

            # 更新服务器文件列表
            self.update_server_file_list()

    def store_file(self, sock: socket.socket, filename: str, local_file_path: str, data_connection_method: Data_connection_method):
        """将本地文件传输到服务器"""
        response = send_command(sock, f"STOR {filename}")
        
        if response.startswith("550 "):
            self.show_error_message(f"无法存储文件: {response}")
            return False
        elif response.startswith("150 "):
            # 建立数据连接
            if data_connection_method.method == Method.PORT:
                data_sock_listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                data_sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                data_sock_listen.bind((data_connection_method.ip_address, data_connection_method.port_number))
                data_sock_listen.listen(1)
                data_sock, addr = data_sock_listen.accept()
                print("PORT模式数据连接已建立.")
            elif data_connection_method.method == Method.PASV:
                data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                data_sock.connect((data_connection_method.ip_address, data_connection_method.port_number))
                print("PASV模式数据连接已建立.")
            else:
                self.show_error_message("必须先建立数据连接才能传输数据.")
                return False

            # 开始传输文件
            with open(local_file_path, 'rb') as f:
                while True:
                    data = f.read(BUFFER_SIZE)
                    if not data:
                        break
                    data_sock.sendall(data)
                    print(f"已发送 {len(data)} 字节")

            data_sock.close()
            if data_connection_method.method == Method.PORT:
                data_sock_listen.close()

            # 检查传输是否成功
            response = receive_response(sock)
            if response.startswith("226 "):
                print(f"文件 {filename} 存储成功.")
            else:
                self.show_error_message("存储文件时发生错误.")
            
            return True
        else:
            self.show_error_message(f"STOR命令失败: {response}")
            return False
        
    def handle_retr(self):
        """处理RETR按钮点击事件，用于从服务器取回文件"""
        # 检查是否选中了服务器上的文件
        selected_item = self.server_list.currentItem()
        if selected_item is None:
            self.show_error_message("未选择任何文件。请先选择服务器上的一个文件。")
            return

        server_file_name = selected_item.text()

        # 弹出输入框，获取本地存储路径，默认路径为当前本地文件栏路径下
        default_local_path = os.path.join(self.current_local_dir, server_file_name)
        local_file_path, ok = QInputDialog.getText(self, 'RETR', f'请输入文件存储路径:', text=default_local_path)

        if ok and local_file_path:
            # 发送PASV或PORT命令
            if self.data_connection_method.method == Method.PASV:
                if not self.handle_pasv():
                    self.show_error_message("PASV 模式设置失败.")
                    return
            elif self.data_connection_method.method == Method.PORT:
                if not self.handle_port():
                    self.show_error_message("PORT 模式设置失败.")
                    return

            # 发送RETR命令并开始文件传输
            self.retrieve_file(self.sock, server_file_name, local_file_path, self.data_connection_method)

            # 更新本地文件列表
            self.update_local_file_list()

    def retrieve_file(self, sock: socket.socket, filename: str, local_file_path: str, data_connection_method: Data_connection_method):
        """从服务器检索文件到本地"""
        response = send_command(sock, f"RETR {filename}")

        if response.startswith("550 "):
            self.show_error_message(f"无法检索文件: {response}")
            return False
        elif response.startswith("150 "):
            # 建立数据连接
            if data_connection_method.method == Method.PORT:
                data_sock_listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                data_sock_listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                data_sock_listen.bind((data_connection_method.ip_address, data_connection_method.port_number))
                data_sock_listen.listen(1)
                data_sock, addr = data_sock_listen.accept()
                print("PORT模式数据连接已建立.")
            elif data_connection_method.method == Method.PASV:
                data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                data_sock.connect((data_connection_method.ip_address, data_connection_method.port_number))
                print("PASV模式数据连接已建立.")
            else:
                self.show_error_message("必须先建立数据连接才能传输数据.")
                return False

            # 开始接收文件并存储到本地
            with open(local_file_path, 'wb') as f:
                while True:
                    data = data_sock.recv(BUFFER_SIZE)
                    if not data:
                        break
                    f.write(data)
                    print(f"已接收 {len(data)} 字节")

            data_sock.close()
            if data_connection_method.method == Method.PORT:
                data_sock_listen.close()

            # 检查传输是否成功
            response = receive_response(sock)
            if response.startswith("226 "):
                print(f"文件 {filename} 已成功取回.")
            else:
                self.show_error_message("取回文件时发生错误.")

            return True
        else:
            self.show_error_message(f"RETR命令失败: {response}")
            return False

    def list_files(self):
        """从服务器获取文件列表并显示在界面上"""
        try:
            response = send_command(self.sock, "LIST")
            if response.startswith("150 "):
                # 通过PASV模式连接数据端口
                data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                data_sock.connect((self.data_connection_method.ip_address, self.data_connection_method.port_number))
                print("数据连接已建立。")

                # 接收文件列表数据
                file_list = ''
                while True:
                    data = data_sock.recv(BUFFER_SIZE).decode()
                    if not data:
                        break
                    file_list += data

                print(file_list)
                data_sock.close()

                # 检查文件列表传输完成的响应
                response = receive_response(self.sock)
                if response.startswith("226 "):
                    print("文件列表成功获取。")

                    # 清空并更新服务器文件列表视图
                    self.server_list.clear()

                    # 解析文件列表并更新UI
                    file_lines = file_list.strip().splitlines()
                    for line in file_lines:
                        # 假设每行是标准的`LIST`输出格式，如: drwxr-xr-x  2 user group 4096 Oct 14 12:00 folder_name
                        parts = line.split()
                        file_name = parts[-1]
                        list_item = QListWidgetItem(file_name)
                        if line.startswith('d'):  # 如果是目录
                            list_item.setForeground(QColor("blue"))  # 文件夹颜色为蓝色
                            list_item.setFont(QFont('Arial', 13, QFont.Bold))  # 文件夹加粗显示
                        else:
                            list_item.setForeground(QColor("black"))  # 文件颜色为黑色
                        self.server_list.addItem(list_item)

                    return True
                else:
                    raise Exception("Failed to complete file list transfer.")
            else:
                raise Exception("Failed to retrieve file list.")
        except Exception as e:
            print(f"Error: {e}")
            self.show_error_message(str(e))

            # 清空服务器文件列表并仅显示"."和".."
            self.server_list.clear()
            dot_item = QListWidgetItem(".")
            dot_item.setFont(QFont('Arial', 13, QFont.Bold))
            dot_item.setForeground(QColor("blue"))  # 设置为蓝色表示目录
            self.server_list.addItem(dot_item)

            # 添加".."的项并设置样式
            dotdot_item = QListWidgetItem("..")
            dotdot_item.setFont(QFont('Arial', 13, QFont.Bold))
            dotdot_item.setForeground(QColor("blue"))  # 设置为蓝色表示目录
            self.server_list.addItem(dotdot_item)
            return False
    
    def handle_pwd(self):
        """处理PWD按钮点击事件"""
        try:
            # 发送PWD命令到服务器
            response = send_command(self.sock, "PWD")
            
            if response.startswith("257 "):
                # 提取路径
                start = response.find('"') + 1
                end = response.find('"', start)
                current_path = response[start:end]

                # 弹出消息框显示路径
                self.show_info_message(f"当前工作路径: {current_path}")
            else:
                raise Exception("Failed to retrieve current directory.")
        except Exception as e:
            print(f"Error: {e}")
            self.show_error_message(str(e))

    def navigate_server_directory(self, item):
        """处理服务器文件列表中的双击事件，切换到相应的目录"""
        selected_item = item.text()

        try:
            # 发送CWD命令切换目录
            self.change_directory_on_server(selected_item)

            # 切换目录成功后更新服务器文件列表
            self.update_server_file_list()
        except Exception as e:
            print(f"Error: {e}")
            self.show_error_message(str(e))

    def change_directory_on_server(self, directory):
        """向服务器发送CWD命令以切换工作目录"""
        response = send_command(self.sock, f"CWD {directory}")
        
        if response.startswith("250 "):
            print(f"Changed directory to {directory}")
        else:
            raise Exception(f"Failed to change directory to {directory}: {response}")

    def create_new_directory(self):
        """弹出输入框并新建文件夹"""
        # 弹出输入框，获取文件夹名称
        folder_name, ok = QInputDialog.getText(self, '新建文件夹', '请输入新文件夹的名称:')
        
        # 检查输入是否有效
        if ok and folder_name:
            if self.is_valid_folder_name(folder_name):
                try:
                    # 尝试在服务器上创建文件夹
                    if self.make_directory(self.sock, folder_name):
                        # 创建成功后更新服务器文件列表
                        self.update_server_file_list()
                    else:
                        self.show_error_message(f"Failed to create directory: {folder_name}")
                except Exception as e:
                    self.show_error_message(f"Error: {e}")
            else:
                self.show_error_message("无效的文件夹名称。")
        elif ok:
            self.show_error_message("未输入文件夹名称。")

    def is_valid_folder_name(self, folder_name):
        """检查文件夹名称是否合法"""
        if folder_name.startswith('/'):
            return False        
        invalid_chars = ['\\', ':', '*', '?', '"', '<', '>', '|']
        return not any(char in folder_name for char in invalid_chars)

    def make_directory(self, sock, directory):
        """向服务器发送MKD命令以创建文件夹"""
        response = send_command(sock, f"MKD {directory}")
        if response.startswith("257 "):
            print(f"Directory {directory} created successfully.")
            return True
        else:
            print(f"Failed to create directory {directory}: {response}")
            return False
        
    def delete_directory(self):
        """弹出输入框并删除文件夹"""
        # 弹出输入框，获取要删除的文件夹名称
        folder_name, ok = QInputDialog.getText(self, '删除文件夹', '请输入要删除的文件夹名称:')
        
        # 检查输入是否有效
        if ok and folder_name:
            if self.is_valid_folder_name(folder_name):
                # 确认删除操作
                reply = QMessageBox.question(self, '确认删除', f'确定要删除文件夹 "{folder_name}" 吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    try:
                        # 尝试在服务器上删除文件夹
                        if self.remove_directory(self.sock, folder_name):
                            # 删除成功后更新服务器文件列表
                            self.update_server_file_list()
                        else:
                            self.show_error_message(f"Failed to delete directory: {folder_name}")
                    except Exception as e:
                        self.show_error_message(f"Error: {e}")
            else:
                self.show_error_message("无效的文件夹名称。")
        elif ok:
            self.show_error_message("未输入文件夹名称。")

    def remove_directory(self, sock, directory):
        """向服务器发送RMD命令以删除文件夹"""
        response = send_command(sock, f"RMD {directory}")
        if response.startswith("250 "):
            print(f"Directory {directory} deleted successfully.")
            return True
        else:
            print(f"Failed to delete directory {directory}: {response}")
            return False
        
    def handle_quit(self):
        """处理退出按钮点击事件，向服务器发送QUIT并关闭客户端"""
        try:
            send_command(self.sock, "QUIT")  # 发送QUIT命令到服务器
            self.sock.close()  # 关闭socket连接
            self.close()  # 关闭客户端界面
        except Exception as e:
            self.show_error_message(f"退出时出错: {e}")

    def handle_refresh(self):
        """处理刷新按钮点击事件，刷新本地和服务器文件列表"""
        self.update_local_file_list()  # 刷新本地文件列表
        self.update_server_file_list()  # 刷新服务器文件列表
        
    def show_info_message(self, message):
        """显示信息提示框"""
        info_dialog = QMessageBox()
        info_dialog.setIcon(QMessageBox.Information)
        info_dialog.setText(message)
        info_dialog.setWindowTitle("Information")
        info_dialog.exec_()

    def show_error_message(self, message):
        """显示错误提示框"""
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText(message)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()

def parse_arguments():
    """解析命令行参数"""
    ip_address = DEFAULT_IP
    port_number = DEFAULT_PORT

    for i in range(1, len(sys.argv)):
        if sys.argv[i] == '-ip' and i + 1 < len(sys.argv):
            ip_address = sys.argv[i + 1]
        elif sys.argv[i] == '-port' and i + 1 < len(sys.argv):
            port_number = int(sys.argv[i + 1])

    return ip_address, port_number

if __name__ == '__main__':
    app = QApplication(sys.argv)
    server_ip, server_port = parse_arguments()

    login_window = LoginWindow(server_ip, server_port)
    login_window.show()

    sys.exit(app.exec_())
