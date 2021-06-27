#!/bin/bash

# Parameters
wait_time=20
out=./out/Default
# out=./out/Exp

TEST=0
WAIT_TIME=20
COMPILE=0
while [[ $# -gt 0 ]]
do
    key=$1
    case $key in
        -t|--test)
            TEST=1
            shift
            ;;
        -c|--compile)
            COMPILE=1
            shift
            ;;
        -w|--wait)
            WAIT_TIME=$2
            shift
            shift
            ;;
    esac
done


out=./out/Default
project_log_dir=~/Data/webrtc_exp4
sudo modprobe v4l2loopback devices=2
sudo chown lix16:lix16 /dev/video1

conduct_exp()
{
    echo Conduct experiment with resolution: $resolution, bitrate: $bitrate
    ts=$(date +%F_%H-%M-%S)

    # Compilation
    if [[ "$COMPILE" == "1" || "$TEST" == "0" ]]; then
        sed -i "246s/.*/  max_bitrate = $bitrate;/" media/engine/webrtc_video_engine.cc
        ninja -C $out -j$(nproc)
    fi
    log_dir=${project_log_dir}/$ts
    mkdir -p $log_dir
    rm ${project_log_dir}/latest
    ln -s $log_dir ${project_log_dir}/latest

    tmux send-keys -t 0:0 C-c
    tmux send-keys -t 0:1 C-c
    tmux send-keys -t 0:2 C-c
    tmux send-keys -t 0:3 C-c
    tmux send-keys -t 0:4 C-c
    tmux send-keys -t 0:5 C-c

    tmux send-keys -t 0:3 'cd ~/Workspace/webrtc-controller/python_src && conda activate dev && python -m experiment.fakewebcam' Enter
    sleep 1
    tmux send-keys -t 0:0 'cd ~/Workspace/webrtc/src && '${out}'/peerconnection_server_headless' Enter
    sleep 1
    tmux send-keys -t 0:1 'cd ~/Workspace/webrtc/src && sudo '${out}'/peerconnection_client_headless --receiving_only --name RECEIVER --server 127.0.0.1 --logger '$log_dir'/client1.logb > '$log_dir'/client1.log 2>&1' Enter
    sleep 1
    tmux send-keys -t 0:2 'cd ~/Workspace/webrtc/src && sudo '${out}'/peerconnection_client_headless --name SENDER --resolution '$resolution' --server 127.0.0.1 --logger '$log_dir'/client2.logb > '$log_dir'/client2.log 2>&1' Enter
    sleep 1
    tmux send-keys -t 0:4 'cd ~/Workspace/yolov5 && conda activate dev && python -m dump -o '$log_dir'/dump' Enter
    tmux send-keys -t 0:5 'cd ~/Workspace/NetworkMonitor/build && sudo ./NetworkMonitor --dev lo --protocol udp > '$log_dir'/network_client.log' Enter

    echo Wait for ${WAIT_TIME}s
    sleep $WAIT_TIME
    echo Finished

    echo ts=$ts > $log_dir/metadata.txt
    echo resolution=$resolution >> $log_dir/metadata.txt
    echo bitrate=$bitrate >> $log_dir/metadata.txt
    echo codec=h264 >> $log_dir/metadata.txt

    echo Kill processes
    sudo killall -SIGINT peerconnection_client_headless
    sleep .2
    killall -SIGINT peerconnection_server_headless
    sleep .2
    killall -SIGINT python
    sleep .2
    killall -SIGINT python
    sleep .2
    sudo killall -SIGINT NetworkMonitor

    if [[ "$TEST" == "0" ]]; then
        frames=$(ls "$log_dir"/dump|wc -l)
        if [ "$frames" -lt "100" ]; then
            echo 'Not enough frames transmitted, redo experiment'
            conduct_exp
        fi
    fi
}

declare -a resolutions=("480x320" "720x480" "960x640" "1200x800" "1440x1280" "1680x1120" "1920x1280")
declare -a bitrates=("500" "1000" "1500" "2000" "2500" "3000" "3500" "4000" "4500" "5000" "5500" "6000" "7000" "8000" "9000" "10000")
# declare -a resolutions=("480x320" "960x640" "1440x1280" "1920x1280")
# declare -a bitrates=("1000" "2000" "3000" "4000" "5000" "6000")

if [[ "$TEST" == "1" ]]; then
    resolution=1920x1280
    bitrate=5000
    conduct_exp
else
    for r in "${resolutions[@]}"; do
        for b in "${bitrates[@]}"; do
            resolution=$r
            bitrate=$b
            conduct_exp
        done
    done
fi


