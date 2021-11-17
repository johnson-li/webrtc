cmake_minimum_required(VERSION 3.10)

# set the project name
project(WebRTC-Controller)

# add the executable
add_executable(Benchmark-server benchmark-server)

add_executable(Benchmark-client benchmark-client)

add_executable(Echo-server udp-echo-server)

