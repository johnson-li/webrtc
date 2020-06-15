#include <string>
#include <sys/socket.h> 
#include <netinet/tcp.h>
#include <netinet/in.h> 
#include <arpa/inet.h> 
#include <iostream>
#include "base/debug/stack_trace.h"

int COUNT = 20;

int main(int argc, char* argv[]) {
  if (argc < 2) {
    std::cerr << "Usage: ./sync_client target_ip" << std::endl;
    exit(-1);
  }
  const std::string target = argv[1];
  int port = 3434;
  struct sockaddr_in serv_addr; 
  int fd;
  int opt = 1;
  if ((fd = socket(AF_INET, SOCK_STREAM, 0)) < 0) 
  { 
      printf("Socket creation error \n"); 
      return -1; 
  } 
  if (setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &opt, sizeof(opt))) {
      perror("Set TCP_NODELAY"); 
      exit(EXIT_FAILURE); 
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
  int64_t ts[COUNT];
  int64_t rts[COUNT];
  int64_t diff1[COUNT - 5];
  int64_t diff2[COUNT - 5];
  char buffer[8] = {0}; 
  for (int i = 0; i < COUNT; i++) {
    ts[i] = base::debug::Logger::getLogger()->getTimestampMs();
    send(fd, ts + i, sizeof(int64_t), 0); 
    read(fd, buffer, 8); 
    rts[i] = *reinterpret_cast<int64_t*>(buffer);
  }
  std::cout << "ts = [";
  for (int i = 4; i < COUNT - 1; i++) {
    std::cout << ts[i] << ", ";
  }
  std::cout << "]" << std::endl;
  std::cout << "rts = [";
  for (int i = 4; i < COUNT - 1; i++) {
    std::cout << rts[i] << ", ";
  }
  std::cout << "]" << std::endl;

  for (int i = 4; i < COUNT - 1; i++) {
    diff1[i - 4] = (ts[i] + ts[i + 1]) / 2 - rts[i]; 
    diff2[i - 4] = (rts[i] + rts[i + 1]) / 2 - ts[i + 1];
  }
  std::cout << "diff1 = [";
  double s1 = 0, s2 = 0;
  for (int i = 0; i < COUNT - 5; i++) {
    std::cout << diff1[i] << ", ";
    s1 += diff1[i];
  }
  std::cout << "]" << std::endl;
  std::cout << "diff2 = [";
  for (int i = 0; i < COUNT - 5; i++) {
    std::cout << diff2[i] << ", ";
    s2 += diff2[i];
  }
  std::cout << "]" << std::endl;
  s1 /= COUNT - 5;
  s2 /= COUNT - 5;
  std::cout << std::setprecision(10) << s1 << " " << s2 << std::endl;
  return 0;
}
