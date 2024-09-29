import socket

size = 8192

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', 9876))

ssequence_num = 0

try:
  while True:
    data, address = sock.recvfrom(size)
    ssequence_num += 1
    response = f"{ssequence_num} {data.decode()}"
    sock.sendto(response.encode(), address)
finally:
  sock.close()