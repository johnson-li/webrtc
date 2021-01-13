#!/bin/bash

cd python_src
target=/tmp/cc
mode=pour
fps=''
ip=195.148.127.230

# for i in $(seq 1 9) $(seq 10 5 50) $(seq 60 10 80)
for i in $(seq 10 5 50) $(seq 60 10 80)
do
    python -m benchmark.client -s ip -b udp_${mode} -d $((1024*1024*i)) -a 1472
    rm -r ../results/${target}/${mode}_${fps}_${i}m
    cp -r /tmp/webrtc/logs ../results/${target}/${mode}_${fps}_${i}m
    date > ../results/${target}/${mode}_${fps}_${i}m/date.txt
done
