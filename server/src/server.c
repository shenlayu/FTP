#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>

#define DEFAULT_PORT 21
#define DEFAULT_ROOT "./data"
#define BUFFER_SIZE 1024
#define MAX_CLIENTS 10

// TODO: 用docker

// 结构体用于存储客户端信息
typedef struct {
    int socket;
    struct sockaddr_in address;
} client_info;

char *root_directory = DEFAULT_ROOT; // 默认根目录
int port_number = DEFAULT_PORT;        // 默认端口

// 服务器IP地址
char server_ip[INET_ADDRSTRLEN] = "127.0.0.1";

int data_socket = -1;

// 处理PORT命令
void handle_port_command(const char *command, int client_socket, char client_ip[INET_ADDRSTRLEN], int *client_port) {
    int h1, h2, h3, h4, p1, p2;
    if (sscanf(command, "PORT %d,%d,%d,%d,%d,%d", &h1, &h2, &h3, &h4, &p1, &p2) == 6) {
        sprintf(client_ip, "%d.%d.%d.%d", h1, h2, h3, h4);
        *client_port = p1 * 256 + p2;
        send(client_socket, "200 PORT command successful.\r\n", 30, 0);
    } else {
        send(client_socket, "500 Syntax error, command unrecognized.\r\n", 41, 0);
    }
}

// 处理PASV命令
int handle_pasv_command(int client_socket) {
    srand(time(NULL));
    int random_port = rand() % (65535 - 20000 + 1) + 20000;

    int p1 = random_port / 256;
    int p2 = random_port % 256;
    char response[100];
    sprintf(response, "227 Entering Passive Mode (%d,%d,%d,%d,%d,%d).\r\n", 
        atoi(strtok(server_ip, ".")), 
        atoi(strtok(NULL, ".")), 
        atoi(strtok(NULL, ".")), 
        atoi(strtok(NULL, ".")), 
        p1, p2);
    send(client_socket, response, strlen(response), 0);

    // 创建一个新的socket并监听这个随机端口
    data_socket = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in data_addr;
    data_addr.sin_family = AF_INET;
    data_addr.sin_addr.s_addr = INADDR_ANY; // 监听所有接口
    data_addr.sin_port = htons(random_port);
    bind(data_socket, (struct sockaddr *)&data_addr, sizeof(data_addr));
    listen(data_socket, MAX_CLIENTS); // 监听连接

    // while (1) {
    //     client_info *data_cli = malloc(sizeof(client_info));
    //     socklen_t addr_size = sizeof(data_cli->address);
    //     data_cli->socket = accept(data_socket, (struct sockaddr *)&data_cli->address, &addr_size);
        
    //     // pthread_t thread;
    //     // pthread_create(&thread, NULL, handle_client, data_cli);
    //     // pthread_detach(thread);
    // }

    // close(data_socket);
    return data_socket;
}

void handle_retr_command(const char *filename, int client_socket, int data_socket, client_info *data_cli) {
    char filepath[BUFFER_SIZE];
    sprintf(filepath, "%s/%s", root_directory, filename);

    socklen_t addr_size = sizeof(data_cli->address);

    FILE *file = fopen(filepath, "rb");
    if (file == NULL) {
        send(client_socket, "550 File not found or permission denied.\r\n", 42, 0);
        return;
    }
    send(client_socket, "150 Opening binary mode data connection.\r\n", 42, 0);

    char buffer[BUFFER_SIZE];
    size_t bytes_read;

    while ((bytes_read = fread(buffer, 1, BUFFER_SIZE, file)) > 0) {
        send(data_socket, buffer, bytes_read, 0);
    }

    fclose(file);
    close(data_socket); // 关闭数据连接

    send(client_socket, "226 Transfer complete.\r\n", 24, 0);
}

void handle_stor_command(const char *filename, int client_socket, int data_socket, client_info *data_cli) {
    char filepath[BUFFER_SIZE];
    sprintf(filepath, "%s/%s", root_directory, filename);

    socklen_t addr_size = sizeof(data_cli->address);

    FILE *file = fopen(filepath, "wb");
    if (file == NULL) {
        send(client_socket, "550 Failed to open file.\r\n", 26, 0);
        return;
    }
    send(client_socket, "150 Ready to receive data.\r\n", 28, 0);
    
    data_cli->socket = accept(data_socket, (struct sockaddr *)&data_cli->address, &addr_size);

    char buffer[BUFFER_SIZE];
    ssize_t bytes_received;
    while ((bytes_received = recv(data_cli->socket, buffer, BUFFER_SIZE, 0)) > 0) {
        fwrite(buffer, 1, bytes_received, file);
        printf("bytes");
    }

    fclose(file);
    close(data_cli->socket); // 关闭数据连接

    send(client_socket, "226 Transfer complete.\r\n", 24, 0);
}

// 处理单个客户端多次请求的函数
void *handle_client(void *arg) {
    client_info *cli = (client_info *)arg;
    char buffer[BUFFER_SIZE];
    int logged_in = 0;

    client_info *data_cli = (client_info *)malloc(sizeof(client_info));
    // char data_buffer[BUFFER_SIZE];

    // 用于存储客户端的IP地址和端口
    int constructing_data_socket = 0; // 为0时表示未经过PORT，不需建立data_socket；否则表示需要建立data_socket
    char client_ip[INET_ADDRSTRLEN];
    int client_port;

    // 已建立数据连接
    int constructed_data_socket = 0;
    int data_socket = -1;

    // 发送欢迎消息
    send(cli->socket, "220 Anonymous FTP server ready.\r\n", 33, 0);

    while (1) {
        memset(buffer, 0, sizeof(buffer));
        int bytes_received = recv(cli->socket, buffer, sizeof(buffer) - 1, 0);
        int data_bytes_received = 0;
        
        // memset(data_buffer, 0, sizeof(data_buffer));
        // if(constructed_data_socket) {
        //     data_bytes_received = recv(cli->socket, data_buffer, sizeof(data_buffer) - 1, 0);
        // }
        
        if (bytes_received <= 0 && data_bytes_received <= 0) {
            continue;
        }
        
        // printf("received %s\n", buffer);

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
                handle_port_command(buffer, cli->socket, client_ip, &client_port);
                constructing_data_socket = 1;
            } else if (strncmp(buffer, "PASV", 4) == 0) {
                data_socket = handle_pasv_command(cli->socket);
                constructed_data_socket = 1;
                // data_cli->socket = accept(data_socket, (struct sockaddr *)&data_cli->address, NULL);
                // printf("data_cli->socket: %d\n", data_cli->socket);
            } else if (strncmp(buffer, "RETR", 4) == 0) {
                char filename[BUFFER_SIZE];
                sscanf(buffer, "RETR %s", filename);
                if(constructed_data_socket) {
                    if (data_cli->socket == -1) {
                        perror("Data socket not established");
                        send(cli->socket, "425 Can't open data connection.\r\n", 33, 0);
                    }
                    handle_retr_command(filename, cli->socket, data_socket, data_cli);
                } else if(constructing_data_socket) {

                } else {
                    send(cli->socket, "500 Data connection must be established before transporting data.\r\n", 67, 0);
                }
            } else if (strncmp(buffer, "STOR", 4) == 0) {
                char filename[BUFFER_SIZE];
                sscanf(buffer, "STOR %s", filename);
                if(constructed_data_socket) {
                    if (data_cli->socket == -1) {
                        perror("Data socket not established");
                        send(cli->socket, "425 Can't open data connection.\r\n", 33, 0);
                    }
                    handle_stor_command(filename, cli->socket, data_socket, data_cli);
                } else if(constructing_data_socket) {

                } else {
                    send(cli->socket, "500 Data connection must be established before transporting data.\r\n", 67, 0);
                }
                // send(cli->socket, "500 Data connection must be established before transporting data.\r\n", 67, 0);
            } else if(strcmp(buffer, "QUIT") == 0) {
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
