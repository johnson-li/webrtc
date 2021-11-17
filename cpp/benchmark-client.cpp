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
#include <getopt.h>
#include <string>
#include <algorithm>
#include "benchmark.hpp"

unsigned long long recv_ts[1024 * 1024 * 100];
unsigned long long send_ts[1024 * 1024 * 100];

int main(int argc, char **argv) {
  int c;
  std::string server = "127.0.0.1";
  int port = PORT;
  int packet_size = 1400;
  int duration = 15;
  bool active = false;
  long long bitrate = 1024 * 1024;
  while (1) {
    static struct option long_options[] = {
      {"server", required_argument, 0, 's'},
      {"port", required_argument, 0, 'p'},
      {"packet-size", required_argument, 0, 'k'},
      {"duration", required_argument, 0, 't'},
      {"bitrate", required_argument, 0, 'b'},
      {"active", required_argument, 0, 'a'},
      {0, 0, 0, 0}
    };
    int option_index = 0;
    c = getopt_long (argc, argv, "ab:t:k:p:s:", long_options, &option_index);
    if (c == -1)
      break;
    switch (c) {
      case 0: 
        if (long_options[option_index].flag != 0)
          break;
      case 's': 
        server = optarg;
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

  struct sockaddr_in server_addr;
  struct hostent *host;
  unsigned int max_recv_seq = 0;
  unsigned char *send_data = (unsigned char *)calloc(packet_size, sizeof(unsigned char));
  host = (struct hostent *) gethostbyname(server.c_str());
  int sock = socket(AF_INET, SOCK_DGRAM, 0);
  fcntl(sock, F_SETFL, O_NONBLOCK);
  server_addr.sin_family = AF_INET;
  server_addr.sin_port = htons(port);
  server_addr.sin_addr = *((struct in_addr *)host->h_addr);
  memset(&(server_addr.sin_zero),0,sizeof(server_addr.sin_zero));
  sendto(sock, send_data, packet_size, 0,
      (struct sockaddr *)&server_addr, sizeof(struct sockaddr));

  unsigned int seq = 0;
  int bytes_read;
  int addr_len;
  char recv_data[1024 * 1024];
  double start_ts = get_monotonic_time();
  struct sockaddr_in remote_addr;
  while (get_monotonic_time() - start_ts <= duration) {
    bytes_read = recvfrom(sock, recv_data, 1024 * 1024, 0, 
        (struct sockaddr *)&remote_addr, (socklen_t *)&addr_len);
    if (bytes_read > 0 ) {
        unsigned int remote_seq = 0;
        for (int i = 0; i < SEQ_LENGTH; i++) {
          remote_seq <<= 8;
          remote_seq |= recv_data[7 - i] & 0xffU;
        } 
        recv_ts[remote_seq] = get_monotonic_time_us();
        max_recv_seq = std::max(remote_seq, max_recv_seq);
    }
    if (active) {
      auto now = get_monotonic_time();
      auto wait = seq * packet_size * 8 / (double)bitrate - (now - start_ts);
      if (wait <= 0) {
        for (int i = 0; i < SEQ_LENGTH; i++) {
          send_data[i] = (seq >> (i * 8));
        } 
        sendto(sock, send_data, packet_size, 0,
            (struct sockaddr *)&server_addr, sizeof(struct sockaddr));
        send_ts[seq] = get_monotonic_time_us();
        seq++;
      }
    }
  }
  printf("send seq: %d, recv seq: %d", seq, max_recv_seq);
  dump("bc_client_recv_ts.txt", recv_ts, max_recv_seq);
  dump("bc_client_send_ts.txt", send_ts, seq);
  exit(0);
}
