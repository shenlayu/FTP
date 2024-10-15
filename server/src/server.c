#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <dirent.h>
#include <sys/types.h>
#include <sys/stat.h>

#define DEFAULT_PORT 21
#define DEFAULT_ROOT "./data"
#define BUFFER_SIZE 8192
#define MAX_CLIENTS 10

// 结构体用于存储客户端信息
typedef struct {
    int socket;
    struct sockaddr_in address;
} client_info;

typedef enum {
    PASV,
    PORT,
    NOTHING
} Method;

typedef struct {
    Method method;        // 取值为 PASV, PORT 或 NOTHING
    int data_socket;
    char ip_address[INET_ADDRSTRLEN];
    int port_number;
} Data_connection_method;

char *root_directory = DEFAULT_ROOT; // 默认根目录
int port_number = DEFAULT_PORT;        // 默认端口

char abs_root[BUFFER_SIZE];
char current_dir[BUFFER_SIZE];

// 服务器IP地址
char server_ip[INET_ADDRSTRLEN] = "127.0.0.1";

// 处理PORT命令
void handle_port_command(const char *command, int client_socket, Data_connection_method *data_connection_method) {
    int h1, h2, h3, h4, p1, p2;
    if (sscanf(command, "PORT %d,%d,%d,%d,%d,%d", &h1, &h2, &h3, &h4, &p1, &p2) == 6) {
        sprintf(data_connection_method->ip_address, "%d.%d.%d.%d", h1, h2, h3, h4);
        data_connection_method->port_number = p1 * 256 + p2;
        data_connection_method->method = PORT;
        send(client_socket, "200 PORT command successful.\r\n", 30, 0);
    } else {
        send(client_socket, "500 Syntax error, command unrecognized.\r\n", 41, 0);
    }
}

// 处理PASV命令
void handle_pasv_command(int client_socket, Data_connection_method *data_connection_method) {
    srand(time(NULL));
    int random_port = rand() % (65535 - 20000 + 1) + 20000;
    int data_socket = 0;

    while (1) {
        random_port = rand() % (65535 - 20000 + 1) + 20000;

        // 创建一个新的socket并监听这个随机端口
        data_socket = socket(AF_INET, SOCK_STREAM, 0);
        struct sockaddr_in data_addr;
        data_addr.sin_family = AF_INET;
        data_addr.sin_addr.s_addr = INADDR_ANY; // 监听所有接口
        data_addr.sin_port = htons(random_port);
        if (bind(data_socket, (struct sockaddr *)&data_addr, sizeof(data_addr)) == 0) {
            listen(data_socket, MAX_CLIENTS); // 监听连接
            break;
        } else {
            close(data_socket);  // Port is already in use, try another
        }
    }

    int p1 = random_port / 256;
    int p2 = random_port % 256;
    char response[100];
    int ip1, ip2, ip3, ip4;
    sscanf(server_ip, "%d.%d.%d.%d", &ip1, &ip2, &ip3, &ip4);
    sprintf(response, "227 Entering Passive Mode (%d,%d,%d,%d,%d,%d).\r\n", ip1, ip2, ip3, ip4, p1, p2);

    send(client_socket, response, strlen(response), 0);

    data_connection_method->data_socket = data_socket;
    data_connection_method->method = PASV;
}

// 建立数据连接
int build_data_connection(int client_socket, Data_connection_method *data_connection_method, client_info *data_cli) {
    if (data_connection_method->method == PASV) {
        socklen_t addr_size = sizeof(data_cli->address);
        data_cli->socket = accept(data_connection_method->data_socket, (struct sockaddr *)&data_cli->address, &addr_size);
    } else if(data_connection_method->method == PORT) {
        data_cli->address.sin_family = AF_INET;
        data_cli->address.sin_port = htons(data_connection_method->port_number);
        inet_pton(AF_INET, data_connection_method->ip_address, &data_cli->address.sin_addr);

        int max_attempts = 10;
        int connected = 0;
        for (int i = 0; i < max_attempts; i++) {
            data_connection_method->data_socket = socket(AF_INET, SOCK_STREAM, 0);
            data_cli->socket = data_connection_method->data_socket;
            if (connect(data_cli->socket, (struct sockaddr *)&data_cli->address, sizeof(data_cli->address)) == 0) {
                connected = 1;
                break;
            }
            perror("Retrying connection to client in PORT mode");
            sleep(1);
        }
        if (!connected) {
            perror("Failed to connect to client in PORT mode");
            close(data_connection_method->data_socket);
            return 0;
        }
    } else {
        send(client_socket, "500 Data connection must be established before transporting data.\r\n", 67, 0);
        return 0;
    }

    return 1;
}

void handle_retr_command(
    const char *filename,
    int client_socket,
    Data_connection_method *data_connection_method,
    client_info *data_cli
    ) {
    if (data_connection_method->method == PASV && data_connection_method->data_socket == 0) {
        perror("Data socket not established");
        send(client_socket, "425 Can't open data connection.\r\n", 33, 0);
    }

    char filepath[BUFFER_SIZE];
    sprintf(filepath, "%s/%s", current_dir, filename);

    FILE *file = fopen(filepath, "rb");
    if (file == NULL) {
        send(client_socket, "550 File not found or permission denied.\r\n", 42, 0);
        return;
    }
    send(client_socket, "150 Opening binary mode data connection.\r\n", 42, 0);

    int data_success = build_data_connection(client_socket, data_connection_method, data_cli);
    if(!data_success) {
        return;
    }

    char buffer[BUFFER_SIZE];
    size_t bytes_read;
    while ((bytes_read = fread(buffer, 1, BUFFER_SIZE, file)) > 0) {
        send(data_cli->socket, buffer, bytes_read, 0);
    }

    fclose(file);
    close(data_cli->socket);
    if (data_connection_method->method == PASV) {
        close(data_connection_method->data_socket);
    }

    send(client_socket, "226 Transfer complete.\r\n", 24, 0);
}

void handle_stor_command(
    const char *filename,
    int client_socket,
    Data_connection_method *data_connection_method,
    client_info *data_cli
    ) {
    if (data_connection_method->method == PASV && data_connection_method->data_socket == 0) {
        perror("Data socket not established");
        send(client_socket, "425 Can't open data connection.\r\n", 33, 0);
    }

    char filepath[BUFFER_SIZE];
    sprintf(filepath, "%s/%s", current_dir, filename);

    FILE *file = fopen(filepath, "wb");
    if (file == NULL) {
        send(client_socket, "550 Failed to open file.\r\n", 26, 0);
        return;
    }
    send(client_socket, "150 Ready to receive data.\r\n", 28, 0);
    
    int data_success = build_data_connection(client_socket, data_connection_method, data_cli);
    if(!data_success) {
        return;
    }
    
    char buffer[BUFFER_SIZE];
    ssize_t bytes_received;
    while ((bytes_received = recv(data_cli->socket, buffer, BUFFER_SIZE, 0)) > 0) {
        fwrite(buffer, 1, bytes_received, file);
    }

    fclose(file);
    close(data_cli->socket);
    if (data_connection_method->method == PASV) {
        close(data_connection_method->data_socket);
    }

    send(client_socket, "226 Transfer complete.\r\n", 24, 0);
}

void handle_list_command(
    int client_socket,
    Data_connection_method *data_connection_method,
    client_info *data_cli,
    char *current_dir // 传入当前工作目录
    ) {
    DIR *dir;
    struct dirent *entry;
    struct stat file_stat;
    char file_info[BUFFER_SIZE];

    // 打开当前目录
    dir = opendir(current_dir);
    if (dir == NULL) {
        send(client_socket, "550 Failed to open directory.\r\n", 31, 0);
        return;
    }

    // 建立数据连接
    send(client_socket, "150 Here comes the directory listing.\r\n", 39, 0);
    int data_success = build_data_connection(client_socket, data_connection_method, data_cli);
    if(!data_success) {
        return;
    }

    // 遍历目录项
    while ((entry = readdir(dir)) != NULL) {
        // 获取文件状态
        char full_path[BUFFER_SIZE];
        sprintf(full_path, "%s/%s", current_dir, entry->d_name);
        if (stat(full_path, &file_stat) == -1) {
            continue;  // 跳过错误的文件
        }

        // 构建文件信息，使用Unix风格的 ls -l 格式
        char file_type = (S_ISDIR(file_stat.st_mode)) ? 'd' : '-';
        sprintf(file_info, "%c--------- 1 user group %lld Jan 1 00:00 %s\r\n", 
                file_type, 
                (long long)file_stat.st_size, 
                entry->d_name);

        // 发送文件信息到数据连接
        send(data_cli->socket, file_info, strlen(file_info), 0);
    }

    // 关闭目录
    closedir(dir);

    // 关闭数据连接
    close(data_cli->socket);
    if (data_connection_method->method == PASV) {
        close(data_connection_method->data_socket);
    }

    send(client_socket, "226 Directory send OK.\r\n", 24, 0);
}

// 处理单个客户端多次请求的函数
void *handle_client(void *arg) {
    client_info *cli = (client_info *)arg;
    char buffer[BUFFER_SIZE];
    int logged_in = 0;

    client_info *data_cli = (client_info *)malloc(sizeof(client_info));

    Data_connection_method *data_connection_method = malloc(sizeof(Data_connection_method));
    data_connection_method->method = NOTHING;

    // 发送欢迎消息
    send(cli->socket, "220 Anonymous FTP server ready.\r\n", 33, 0);

    // 初始化 CURRENT_DIR 为 root_directory 的绝对路径
    if (realpath(root_directory, abs_root) != NULL) {
        strcpy(current_dir, abs_root);
        strcpy(root_directory, abs_root);
    } else {
        // 错误处理
        send(cli->socket, "550 Failed to resolve root directory.\r\n", 39, 0);
    }

    while (1) {
        memset(buffer, 0, sizeof(buffer));
        int bytes_received = recv(cli->socket, buffer, sizeof(buffer) - 1, 0);
        int data_bytes_received = 0;
        
        if (bytes_received <= 0 && data_bytes_received <= 0) {
            continue;
        }
        
        if (logged_in == 0) {
            // 用户未登录
            if (strncmp(buffer, "USER anonymous", 14) == 0) { // 要不要改？
                send(cli->socket, "331 Guest login ok, send your complete e-mail address as password.\r\n", 68, 0);
            } else if (strncmp(buffer, "PASS ", 5) == 0) {
                if (strlen(buffer) > 5) {
                    logged_in = 1; // 允许登录
                    send(cli->socket, "230-\r\n", 6, 0);
                    send(cli->socket, "230-Welcome to\r\n", 16, 0);
                    send(cli->socket, "230-School of Software\r\n", 24, 0);
                    send(cli->socket, "230-FTP Archives at ftp.ssast.org\r\n", 35, 0);
                    send(cli->socket, "230-\r\n", 6, 0);
                    send(cli->socket, "230-This site is provided as a public service by School of\r\n", 60, 0);
                    send(cli->socket, "230-Software. Use in violation of any applicable laws is strictly\r\n", 67, 0);
                    send(cli->socket, "230-prohibited. We make no guarantees, explicit or implicit, about the\r\n", 72, 0);
                    send(cli->socket, "230-contents of this site. Use at your own risk.\r\n", 50, 0);
                    send(cli->socket, "230-\r\n", 6, 0);
                    send(cli->socket, "230 Guest login ok, access restrictions apply.\r\n", 48, 0);
                } else {
                    send(cli->socket, "530 Login incorrect.\r\n", 22, 0);
                }
            } else {
                send(cli->socket, "500 Unrecognized command.\r\n", 27, 0);
            }
        } else {
            // 用户已登录
            if (strncmp(buffer, "PORT", 4) == 0) {
                if (data_connection_method->data_socket > 0) {
                    close(data_connection_method->data_socket);
                }
                if (data_cli->socket > 0) {
                    close(data_cli->socket);
                }
                handle_port_command(buffer, cli->socket, data_connection_method);
            } else if (strncmp(buffer, "PASV", 4) == 0) {
                if (data_connection_method->data_socket > 0) {
                    close(data_connection_method->data_socket);
                }
                if (data_cli->socket > 0) {
                    close(data_cli->socket);
                }
                handle_pasv_command(cli->socket, data_connection_method);
            } else if (strncmp(buffer, "RETR", 4) == 0) {
                char filename[BUFFER_SIZE];
                sscanf(buffer, "RETR %s", filename);
                handle_retr_command(filename, cli->socket, data_connection_method, data_cli);
            } else if (strncmp(buffer, "STOR", 4) == 0) {
                char filename[BUFFER_SIZE];
                sscanf(buffer, "STOR %s", filename);
                handle_stor_command(filename, cli->socket, data_connection_method, data_cli);
            } else if (strcmp(buffer, "SYST") == 0) {
                send(cli->socket, "215 UNIX Type: L8\r\n", 19, 0);
            } else if (strncmp(buffer, "TYPE", 4) == 0) {
                char type_code[1];
                sscanf(buffer, "TYPE %s", type_code);

                if (strncmp(type_code, "I", 1) == 0) {
                    send(cli->socket, "200 Type set to I.\r\n", 20, 0);
                } else {
                    send(cli->socket, "504 Command not implemented for that parameter.\r\n", 49, 0);
                }
            } else if (strncmp(buffer, "MKD", 3) == 0) {
                char directory[BUFFER_SIZE];
                sscanf(buffer, "MKD %s", directory);
                
                char path[BUFFER_SIZE];
                sprintf(path, "%s/%s", current_dir, directory);
                
                if (mkdir(path, 0777) == 0) {
                    char response[BUFFER_SIZE];
                    sprintf(response, "257 \"%s\" directory created.\r\n", directory);
                    send(cli->socket, response, strlen(response), 0);
                } else {
                    send(cli->socket, "550 Failed to create directory.\r\n", 33, 0);
                }
            } else if (strncmp(buffer, "CWD", 3) == 0) {
                char directory[BUFFER_SIZE];
                sscanf(buffer, "CWD %s", directory);
                
                char target_path[BUFFER_SIZE];
                if (directory[0] == '/') {
                    sprintf(target_path, "%s%s", root_directory, directory);
                } else {
                    sprintf(target_path, "%s/%s", current_dir, directory);
                }

                char real_path[BUFFER_SIZE];
                struct stat path_stat;
                
                // 解析真实路径并检查路径是否在root_directory下
                if (realpath(target_path, real_path) != NULL && strncmp(real_path, root_directory, strlen(root_directory)) == 0) {
                    // 检查目标路径是否为目录
                    if (stat(real_path, &path_stat) == 0 && S_ISDIR(path_stat.st_mode)) {
                        strcpy(current_dir, real_path);  // 只在确认是目录时才修改current_dir
                        send(cli->socket, "250 Directory successfully changed.\r\n", 37, 0);
                    } else {
                        // 目标路径存在但不是目录
                        send(cli->socket, "550 Not a directory.\r\n", 22, 0);
                    }
                } else {
                    send(cli->socket, "550 Access denied.\r\n", 20, 0);
                }
            } else if (strncmp(buffer, "PWD", 3) == 0) {
                char abs_root[BUFFER_SIZE];

                if (realpath(root_directory, abs_root) == NULL) {
                    send(cli->socket, "550 Failed to resolve root directory.\r\n", 39, 0);
                } else {
                    if (strncmp(current_dir, abs_root, strlen(abs_root)) == 0) {
                        char relative_path[BUFFER_SIZE] = "/";

                        const char *sub_dir = current_dir + strlen(abs_root);
                        if (strlen(sub_dir) > 0) {
                            strcat(relative_path, sub_dir + 1);  // 加上子目录
                        }

                        char response[BUFFER_SIZE];
                        sprintf(response, "257 \"%s\"\r\n", relative_path);
                        send(cli->socket, response, strlen(response), 0);
                    } else {
                        send(cli->socket, "550 Failed to get current directory.\r\n", 38, 0);
                    }
                }
            } else if (strncmp(buffer, "LIST", 4) == 0) {
                handle_list_command(cli->socket, data_connection_method, data_cli, current_dir);
            } else if (strncmp(buffer, "RMD", 3) == 0) {
                char directory[BUFFER_SIZE];
                sscanf(buffer, "RMD %s", directory);
                
                // 创建完整路径，基于当前工作目录
                char path[BUFFER_SIZE];
                sprintf(path, "%s/%s", current_dir, directory);
                
                if (rmdir(path) == 0) {
                    send(cli->socket, "250 Directory successfully removed.\r\n", 37, 0);
                } else {
                    send(cli->socket, "550 Failed to remove directory.\r\n", 33, 0);
                }
            } else if (strncmp(buffer, "QUIT", 4) == 0) {
                send(cli->socket, "200 Quit successeully.\r\n", 24, 0);
                close(cli->socket);
                if (data_cli->socket > 0) {
                    close(data_cli->socket);
                }
                if(data_connection_method->data_socket > 0) {
                    close(data_cli->socket);
                }
                break;
            } else {
                send(cli->socket, "500 Command not implemented for logged-in users.\r\n", 50, 0);
            }
        }
    }

    close(cli->socket);
    free(cli);
    close(data_cli->socket);
    free(data_cli);

    free(data_connection_method);
    return NULL;
}

int main(int argc, char *argv[]) {
    int server_socket;
    struct sockaddr_in server_addr, client_addr;
    socklen_t addr_size = sizeof(client_addr);
    
    // 解析命令行参数
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-port") == 0 && i + 1 < argc) {
            port_number = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-root") == 0 && i + 1 < argc) {
            root_directory = argv[++i];
        }
    }

    server_socket = socket(AF_INET, SOCK_STREAM, 0); // IPv4, TCP
    server_addr.sin_family = AF_INET; // 服务器地址为IPv4
    server_addr.sin_addr.s_addr = INADDR_ANY; // 服务器监听任意IP地址
    server_addr.sin_port = htons(port_number);

    bind(server_socket, (struct sockaddr *)&server_addr, sizeof(server_addr));
    listen(server_socket, MAX_CLIENTS);

    printf("FTP Server listening on port %d, serving root directory: %s\n", port_number, root_directory);

    while (1) {
        client_info *cli = malloc(sizeof(client_info));
        cli->socket = accept(server_socket, (struct sockaddr *)&cli->address, &addr_size);
        
        pthread_t thread;
        pthread_create(&thread, NULL, handle_client, cli);
        pthread_detach(thread); // 线程分离，防止内存泄漏
    }

    close(server_socket);
    return 0;
}
