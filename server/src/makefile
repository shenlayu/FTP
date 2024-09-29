# Makefile for FTP Server

CC = clang
CFLAGS = -Wall -pthread
TARGET = server

# 默认目标
all: $(TARGET)

# 编译目标
$(TARGET): server.c
	$(CC) $(CFLAGS) -o $(TARGET) server.c

# 清理生成的文件
clean:
	rm -f $(TARGET)

# 运行服务器
run: $(TARGET)
	./$(TARGET) -port 21 -root /tmp

.PHONY: all clean run
