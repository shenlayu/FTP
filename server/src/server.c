#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>

#define DEFAULT_PORT 21
#define DEFAULT_ROOT "/tmp"
#define BUFFER_SIZE 1024
#define MAX_CLIENTS 10

// 结构体用于存储客户端信息
typedef struct {
    int socket;
    struct sockaddr_in address;
} client_info;

char *root_directory = DEFAULT_ROOT; // 默认根目录
int port_number = DEFAULT_PORT;        // 默认端口

// 处理客户端请求的函数
void *handle_client(void *arg) {
    client_info *cli = (client_info *)arg;
    char buffer[BUFFER_SIZE];

    // 发送欢迎消息
    send(cli->socket, "220 Welcome to Mini FTP Server\r\n", 35, 0);

    while (1) {
        memset(buffer, 0, sizeof(buffer));
        int bytes_received = recv(cli->socket, buffer, sizeof(buffer) - 1, 0);
        if (bytes_received <= 0) {
            break; // 处理断开连接
        }
        
        // 去掉结尾的换行符
        buffer[strcspn(buffer, "\r\n")] = 0;

        // 解析命令
        if (strncmp(buffer, "USER", 4) == 0) {
            send(cli->socket, "331 Username okay, need password.\r\n", 38, 0);
        } else if (strncmp(buffer, "PASS", 4) == 0) {
            send(cli->socket, "230 User logged in, proceed.\r\n", 32, 0);
        } else if (strncmp(buffer, "RETR", 4) == 0) {
            // 处理 RETR 命令
        } else if (strncmp(buffer, "STOR", 4) == 0) {
            // 处理 STOR 命令
        } else if (strncmp(buffer, "QUIT", 4) == 0) {
            send(cli->socket, "221 Goodbye.\r\n", 16, 0);
            break; // 退出循环
        } 
        // 处理其他命令...
        else {
            send(cli->socket, "502 Command not implemented.\r\n", 31, 0);
        }
    }

    close(cli->socket);
    free(cli);
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

    server_socket = socket(AF_INET, SOCK_STREAM, 0);
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
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
