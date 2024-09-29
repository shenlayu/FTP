import socket

size = 8192

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
  for i in range(51):
    msg = str(i)
    sock.sendto(msg.encode(), ('localhost', 9876))
    print(sock.recv(size))
  sock.close()

except:
  print("cannot reach the server")