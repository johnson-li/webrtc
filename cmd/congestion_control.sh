#!/bin/bash

cd python_src

log_dir=/tmp/cc
mode=sink
fps='0'
target=195.148.127.230

for i in $(seq 1 9) $(seq 10 5 50) $(seq 60 10 80)
do
    python -m benchmark.client -s $target -b udp_${mode} -d $((1024*1024*i)) -a 1472
    rm -r ${log_dir}/${mode}_${fps}_${i}m
    cp -r /tmp/webrtc/logs ${log_dir}/${mode}_${fps}_${i}m
    date > ${log_dir}/${mode}_${fps}_${i}m/date.txt
done

