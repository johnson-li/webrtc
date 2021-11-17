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
#include <getopt.h>
#include <string>
#include "benchmark.hpp"
#include <algorithm>

unsigned long long recv_ts[1024 * 1024 * 100];
unsigned long long send_ts[1024 * 1024 * 100];

int main(int argc, char **argv) {
  int c;
  int port = PORT;
  int packet_size = 1400;
  int duration = 15;
  bool active = false;
  long long bitrate = 1024 * 1024;
  while (1) {
    static struct option long_options[] = {
      {"port", required_argument, 0, 'p'},
      {"packet-size", required_argument, 0, 'k'},
      {"duration", required_argument, 0, 't'},
      {"bitrate", required_argument, 0, 'b'},
      {"active", required_argument, 0, 'a'},
      {0, 0, 0, 0}
    };
    int option_index = 0;
    c = getopt_long (argc, argv, "ab:t:k:p:", long_options, &option_index);
    if (c == -1)
      break;
    switch (c) {
      case 0: 
        if (long_options[option_index].flag != 0)
          break;
      case 'a': 
        active = true;
        break;
      case 'p': 
        port = std::stoi(optarg);
        break;
      case 'k': 
        packet_size = std::stoi(optarg);
        break;
      case 't': 
        duration = std::stoi(optarg);
        break;
      case 'b': 
        bitrate = std::stoll(optarg);
        break;
      case '?': 
        break;
      default:
        abort();
    }
  }
  if (optind < argc) {
    printf ("non-option ARGV-elements: ");
    while (optind < argc)
      printf ("%s ", argv[optind++]);
    putchar ('\n');
    exit(-1);
  }
  int sock;
  int addr_len, bytes_read;
  unsigned char *send_data = (unsigned char *)calloc(packet_size, sizeof(unsigned char));
  unsigned char recv_data[1024 * 1024];
  struct sockaddr_in server_addr , client_addr;
  sock = socket(AF_INET, SOCK_DGRAM, 0);
  int flags = fcntl(sock, F_GETFL);
  flags |= O_NONBLOCK;
  fcntl(sock, F_SETFL, flags);
  server_addr.sin_family = AF_INET;
  server_addr.sin_port = htons(port);
  server_addr.sin_addr.s_addr = INADDR_ANY;
  bzero(&(server_addr.sin_zero), 8);
  bind(sock, (struct sockaddr *) &server_addr, sizeof(struct sockaddr));
  addr_len = sizeof(struct sockaddr);
  printf("Server listening on %d\n", port);
  unsigned int seq = 0;
  unsigned int max_recv_seq = 0;
  double start_ts = 0;
  while (1) {
    bytes_read = recvfrom(sock, recv_data, 1024 * 1024, 0, 
        (struct sockaddr *)&client_addr, (socklen_t *)&addr_len);
    if (bytes_read > 0) {
      if (start_ts == 0) {
        printf("Received initiate packet from client\n");
        start_ts = get_monotonic_time(); 
      } else {
        unsigned int remote_seq = 0;
        for (int i = 0; i < SEQ_LENGTH; i++) {
          remote_seq <<= 8;
          remote_seq |= recv_data[7 - i] & 0xffU;
        } 
        //printf("Received seq: %d\n", remote_seq);
        recv_ts[remote_seq] = get_monotonic_time_us();
        max_recv_seq = std::max(remote_seq, max_recv_seq);
      }
    }

    if (start_ts > 0 && active) {
      auto now = get_monotonic_time();
      if (start_ts > 0 && now - start_ts > duration) {
        start_ts = 0;
        printf("Benchmark finished\n");
        dump("bc_server_recv_ts.txt", recv_ts, max_recv_seq);
        dump("bc_server_send_ts.txt", send_ts, seq);
      }
      auto wait = seq * packet_size * 8 / (double)bitrate - (now - start_ts);
      if (wait <= 0) {
        for (int i = 0; i < SEQ_LENGTH; i++) {
          send_data[i] = (seq >> (i * 8));
        } 
        sendto(sock, send_data, packet_size, 0, (struct sockaddr *)&client_addr, addr_len);
        send_ts[seq] = get_monotonic_time_us();
        seq++;
      }
    }
  }
  exit(0);
}
