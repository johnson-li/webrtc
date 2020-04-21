#include <string>
#include <sys/socket.h> 
#include <netinet/in.h> 
#include <arpa/inet.h> 
#include <iostream>
#include "base/debug/stack_trace.h"

int main(int argc, char* argv[]) {
  if (argc < 2) {
    std::cerr << "Usage: ./sync_client target_ip" << std::endl;
    exit(-1);
  }
  const std::string target = argv[1];
  int port = 3434;
  struct sockaddr_in serv_addr; 
  int fd;
  if ((fd = socket(AF_INET, SOCK_STREAM, 0)) < 0) 
  { 
      printf("Socket creation error \n"); 
      return -1; 
  } 
  serv_addr.sin_family = AF_INET; 
  serv_addr.sin_port = htons(port); 
  if(inet_pton(AF_INET, target.c_str(), &serv_addr.sin_addr)<=0)  
  { 
      printf("\nInvalid address/ Address not supported \n"); 
      return -1; 
  } 
  if (connect(fd, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) 
  { 
      printf("Connection Failed \n"); 
      return -1; 
  } 
  auto ts = base::debug::Logger::getLogger()->getTimestampMs();
  std::string data = std::to_string(ts);
  send(fd, data.c_str(), strlen(data.c_str()), 0); 
  char buffer[1024] = {0}; 
  read(fd , buffer, 1024); 
  ts = base::debug::Logger::getLogger()->getTimestampMs();
  std::string val = buffer;
  int64_t remote_ts = std::stoll(val);
  std::cout << "timestamp diff: " << ts - remote_ts << std::endl;
  return 0;
}
