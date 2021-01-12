#!/bin/bash

cd python_src

for i in $(seq 1 9) $(seq 10 5 50)
do
    python -m benchmark.client -s 195.148.127.230 -b udp_sink -d $((1024*1024*i)) -a 1472
    cp -r /tmp/webrtc/logs ../results/congestion_control2/sink_${i}m
    date > ../results/congestion_control2/sink_${i}m/date.txt
done
