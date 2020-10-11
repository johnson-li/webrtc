/*
 * udpclient.cpp
 * http://www.pythonprasanna.com/Papers%20and%20Articles/Sockets/udpclient.c
 */

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <fcntl.h>

int main()
{
  int sock;
  struct sockaddr_in server_addr;
  struct hostent *host;
  char send_data[1000];
  host= (struct hostent *) gethostbyname((char *)"192.168.1.28");

  for (int i =0; i < sizeof(send_data); i++) {
    send_data[i] = 'a';
  }

  if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) == -1)
  {
    perror("socket");
    exit(1);
  }
  fcntl(sock, F_SETFL, O_NONBLOCK);

  server_addr.sin_family = AF_INET;
  server_addr.sin_port = htons(8080);
  server_addr.sin_addr = *((struct in_addr *)host->h_addr);
  memset(&(server_addr.sin_zero),0,sizeof(server_addr.sin_zero));

   while (1)
   {

       sendto(sock, send_data, strlen(send_data), 0,
              (struct sockaddr *)&server_addr, sizeof(struct sockaddr));
              }
}
