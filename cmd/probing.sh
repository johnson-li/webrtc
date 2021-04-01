#!/bin/bash

log_path=/tmp/webrtc/logs
results_path=~/Workspace/webrtc-controller/results/probing
mkdir -p $log_path
mkdir -p $results_path

# Start GPSD
# gpsd -D 5 -N -n /dev/ttyUSB0


cd python_src
rm "$log_path"/quectel_*
python -m benchmark.quectel -l /tmp/webrtc/logs -d 100 &
quectel_pid="$!"
rm "$log_path"/gps_*
python -m benchmark.gps -l /tmp/webrtc/logs &
gps_pid="$!"
rm $log_path/probing_cli_*
python -m benchmark.client -b probing -s 195.148.127.230 -l /tmp/webrtc/logs
probing_pid="$!"


timeout=10
echo Wait $timeout seconds to finish
sleep $timeout

kill -9 $quectel_pid
kill -9 $gps_pid

cp $log_path/quectel_* $results_path
cp $log_path/gps_* $results_path
