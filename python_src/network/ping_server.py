import socket


bytesToSend = str.encode("H")
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPServerSocket.bind(('0.0.0.0', 8129))
while(True):
    bytesAddressPair = UDPServerSocket.recvfrom(1024)
    message = bytesAddressPair[0]
    address = bytesAddressPair[1]
    UDPServerSocket.sendto(bytesToSend, address)

