#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <fcntl.h>

int main()
{
    printf("Start server\n");
    int sock;
    int addr_len, bytes_read;
    char recv_data[1024];
    char send_data[1500];
    struct sockaddr_in server_addr , client_addr;

  for (int i =0; i < sizeof(send_data); i++) {
    send_data[i] = 'a';
  }

    if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) == -1) {
        perror("Socket");
        exit(1);
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(8084);
    server_addr.sin_addr.s_addr = INADDR_ANY;
    bzero(&(server_addr.sin_zero),8);


    if (bind(sock,(struct sockaddr *)&server_addr,
                sizeof(struct sockaddr)) == -1)
    {
        perror("Bind");
        exit(1);
    }

    addr_len = sizeof(struct sockaddr);

    printf("\nUDPServer Waiting for client on port 8084");

    while (1)
    {

        bytes_read = recvfrom(sock,recv_data,1024,0,
                (struct sockaddr *)&client_addr, (socklen_t *)&addr_len);


        recv_data[bytes_read] = '\0';

        printf("\n(%s , %d) said : ",inet_ntoa(client_addr.sin_addr),
                ntohs(client_addr.sin_port));
        printf("%s\n", recv_data);
  fcntl(sock, F_SETFL, O_NONBLOCK);
        while (1) {
       sendto(sock, send_data, strlen(send_data), 0,
              (struct sockaddr *)&client_addr, sizeof(struct sockaddr));
        }
    }
    return 0;
}
