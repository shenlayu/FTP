### Q:
Answer: How to write a chat program (two clients chat with each other) with UDP?
### A:
server 应当维护一个数据库，用于存储所有可以通信的 client. 首先在服务器构建一个服务进程。
收到一条 request 时，其要同时接收 address 和 data, 将 address 和数据库中每个
client 进行比对，如果比对成功，将 data 发送给它。
client 方面，应当启动接收消息进程。在发送信息时正常发送即可。