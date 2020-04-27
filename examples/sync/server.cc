#include <string>
#include <sys/socket.h> 
#include <netinet/tcp.h>
#include <netinet/in.h> 
#include <arpa/inet.h> 
#include <stdio.h>
#include <errno.h>
#include <iostream>
#include "base/debug/stack_trace.h"

int COUNT = 20;

int main(int argc, char* argv[]) {
  int port = 3434;
  int fd;
  struct sockaddr_in address; 
  int addrlen = sizeof(address); 
  int opt = 1;

  if ((fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) 
    { 
        perror("socket failed"); 
        exit(EXIT_FAILURE); 
    } 
       
  if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, 
                                                  &opt, sizeof(opt))) { 
      perror("setsockopt"); 
      exit(EXIT_FAILURE); 
  } 
  if (setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &opt, sizeof(opt))) {
      perror("Set TCP_NODELAY"); 
      exit(EXIT_FAILURE); 
  }
  address.sin_family = AF_INET; 
  address.sin_addr.s_addr = INADDR_ANY; 
  address.sin_port = htons(port); 
       
  if (bind(fd, (struct sockaddr *)&address,  
                               sizeof(address))<0) { 
      perror("bind failed"); 
      exit(EXIT_FAILURE); 
  } 
  if (listen(fd, 3) < 0) { 
      perror("listen"); 
      exit(EXIT_FAILURE); 
  } 
  int cfd;
  char buffer[8] = {0}; 
  int64_t ts;
  while(true) {
    if ((cfd = accept(fd, (struct sockaddr *)&address,  
					  (socklen_t*)&addrlen))<0) { 
	    perror("accept"); 
		exit(EXIT_FAILURE); 
	} 
    for (int i = 0; i < COUNT; i++) {
	    read(cfd, buffer, 8); 
        ts = base::debug::Logger::getLogger()->getTimestampMs();
	    send(cfd , &ts, sizeof(int64_t), 0 ); 
    }
    close(cfd);
  }
}
