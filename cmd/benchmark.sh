#!/bin/bash

log_path=/tmp/webrtc/logs
results_path=~/Workspace/webrtc-controller/results/benchmark
mkdir -p $log_path
mkdir -p $results_path

cd python_src
#for bitrate in $((1024*10)) $((1024*20)) $((1024*50)) $((1024*100)) $((1024*200)) $((1024*500)) $((1024*1024)) $((1024*1024*2)) $((1024*1024*5)) $((1024*1024*10)) $((1024*1024*20)) $((1024*1024*50))
for bitrate in $((1024*1024*5)) $((1024*1024*10)) $((1024*1024*20)) $((1024*1024*30)) $((1024*1024*40)) $((1024*1024*50))
do
    echo bitrate: $bitrate
    python -m benchmark.client -s 195.148.127.234 -d $bitrate -b udp_sink -l $log_path -t 30
    mkdir -p $results_path/sink/$bitrate
    cp $log_path/udp_client.log $results_path/sink/$bitrate
    cp $log_path/server.log $results_path/sink/$bitrate
    python -m benchmark.client -s 195.148.127.234 -d $bitrate -b udp_pour -l $log_path -t 30
    mkdir -p $results_path/pour/$bitrate
    cp $log_path/udp_client.log $results_path/pour/$bitrate
    cp $log_path/server.log $results_path/pour/$bitrate
done

