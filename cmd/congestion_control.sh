#!/bin/bash

cd python_src

log_dir=~/Workspace/webrtc-controller/results/congestion_control6
mode=sink
fps='0'
target=195.148.127.230

for mode in sink pour
do
    for fps in 0 10
    do
        for i in $(seq 1 9) $(seq 10 5 50) $(seq 60 10 80)
        do
            path=${mode}_${fps}_${i}m
            echo mode: $mode, fps: $fps, bitrate: $((1024*1024*i)), path: $path
            python -m benchmark.client -s $target -b udp_${mode} -d $((1024*1024*i)) -a 1472
            rm -r ${log_dir}/${path}
            cp -r /tmp/webrtc/logs ${log_dir}/${path}
            date > ${log_dir}/${path}/date.txt
        done
    done
done

