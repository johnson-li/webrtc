#include <time.h>
#include <string>
#include <fstream>

int SEQ_LENGTH = 8;
int TIMESTAMP_LENGTH = 8;
int PORT = 8091;

double get_monotonic_time() {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return ts.tv_sec + ts.tv_nsec * 1e-9;
}

long get_monotonic_time_ms() {
  return long(get_monotonic_time() * 1000);
}

long long get_monotonic_time_us() {
  return long(get_monotonic_time() * 1000000);
}

void dump(std::string title, unsigned long long *data, unsigned int length) {
  std::ofstream file;
  file.open("/tmp/webrtc/logs/" + title, std::ios::out);
  for (unsigned int i = 0; i < length; i++) {
    file << data[i] << ", ";
  }
  file.close();
}
