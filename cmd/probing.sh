#!/bin/bash

log_path=/tmp/webrtc/logs
results_path=~/Workspace/webrtc-controller/results/probing
mkdir -p $log_path
mkdir -p $results_path

cd python_src

rm "$log_path"/quectel*
python -m benchmark.quectel -l /tmp/webrtc/logs -d 100 &
quectel_pid="$!"

#for bitrate in $((1024*1024*5)) $((1024*1024*10)) $((1024*1024*20)) $((1024*1024*50))
#do
#    echo bitrate: $bitrate
#    python -m benchmark.client -s 195.148.127.108 -d $bitrate -b udp_sink -l $log_path -t 30
#    mkdir -p $results_path/sink/$bitrate
#    cp $log_path/udp_client.log $results_path/sink/$bitrate
#done

timeout=10
echo Wait $timeout seconds to finish
sleep $timeout

kill -9 $quectel_pid

cp $log_path/quectel* $results_path
