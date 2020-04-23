#include <string>
#include <sys/socket.h> 
#include <netinet/in.h> 
#include <arpa/inet.h> 
#include <stdio.h>
#include <errno.h>
#include <iostream>

#include "base/debug/stack_trace.h"

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
  char buffer[1024] = {0}; 
  while(true) {
    if ((cfd = accept(fd, (struct sockaddr *)&address,  
					  (socklen_t*)&addrlen))<0) { 
	    perror("accept"); 
		exit(EXIT_FAILURE); 
	} 
    auto ts = base::debug::Logger::getLogger()->getTimestampMs();
    std::string data = std::to_string(ts);
	send(cfd , data.c_str() , strlen(data.c_str()) , 0 ); 
	read(cfd, buffer, 1024); 
    std::string val = buffer;
    int64_t remote_ts = std::stoll(val);
    std::cout << "timestamp diff: " << ts - remote_ts << std::endl;
    close(cfd);
  }
}
