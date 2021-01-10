#!/usr/bin/env bash

for i in $(seq 9); do
  python -m benchmark.client -s 195.148.127.230 -b udp_sink -d $((1024 * 1024 * i)) -a 1472
  cp -r /tmp/webrtc/logs ../results/congestion_control/sink_${i}m
  date >../results/congestion_control/sink_${i}m/date.txt
done
