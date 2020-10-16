#!/bin/bash

# Parameters
resolution=1920x1280
bitrate=1000
wait_time=20

conduct_exp()
{
    echo conduct experiment with resolution: $resolution, bitrate: $bitrate

    # Compilation
    sed -i "246s/.*/  max_bitrate = $bitrate;/" media/engine/webrtc_video_engine.cc
    ninja -C out/Default
    log_dir=~/Data/webrtc/$(date +%F_%H-%M-%S)
    mkdir -p $log_dir

    tmux send-keys -t 0:3 'cd ~/Workspace/webrtc-controller/python_src && python -m experiment.fakewebcam' Enter
    sleep 1
    tmux send-keys -t 0:0 'cd ~/Workspace/webrtc/src && ./out/Default/peerconnection_server_headless' Enter
    sleep 1
    tmux send-keys -t 0:1 'cd ~/Workspace/webrtc/src && ./out/Default/peerconnection_client_headless --receiving_only --server 127.0.0.1 --logger '$log_dir'/client1.logb > '$log_dir'/client1.log 2>&1' Enter
    sleep 1
    tmux send-keys -t 0:2 'cd ~/Workspace/webrtc/src && ./out/Default/peerconnection_client_headless --resolution $resolution --server 127.0.0.1 --logger '$log_dir'/client2.logb > '$log_dir'/client2.log 2>&1' Enter
    sleep 1
    tmux send-keys -t 0:4 'cd ~/Workspace/yolov5 && conda activate dev8 && python -m dump -o '$log_dir'/dump' Enter

    echo wait for ${wait_time}s
    sleep $wait_time

    echo "" > $log_dir/metadata.txt
    echo resolution=$resolution >> $log_dir/metadata.txt
    echo bitrate=4000 >> $log_dir/metadata.txt
    echo codec=h264 >> $log_dir/metadata.txt

    echo kill processes
    killall -SIGINT peerconnection_client_headless
    killall -SIGINT peerconnection_server_headless
    killall -SIGINT python
    killall -SIGINT python
}

# declare -a resolutions=("480x320" "720x480" "960x640" "1200x800" "1440x1280" "1680x1120" "1920x1280")
# declare -a bitrates=("500" "1000" "1500" "2000" "2500" "3000" "3500" "4000" "4500" "5000" "5500" "6000")
declare -a resolutions=("480x320" "960x640" "1440x1280" "1920x1280")
declare -a bitrates=("1000" "2000" "3000" "4000" "5000" "6000")

for r in "${resolutions[@]}"; do
    for b in "${bitrates[@]}"; do
        resolution=$r
        bitrate=$b
        conduct_exp
        break
    done
    break
done
