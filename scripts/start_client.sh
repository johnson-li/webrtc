#!/bin/bash

mv /tmp/webrtc/logs "/tmp/webrtc/$(date).logs"
mkdir -p /tmp/webrtc/logs/yolo
mkdir -p /tmp/webrtc/logs/gps
mkdir -p /tmp/webrtc/logs/sync

session_name=mobix
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
tmux send-key -t ${session_name}:0 'cd ~; conda activate dev' Enter
for i in $(seq 9); do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'cd ~; conda activate dev' Enter
done
tmux send-key -t ${session_name}:0 'while true; do ~/bin/sync_client 195.148.127.233 > /tmp/webrtc/logs/sync/$(date +"%Y-%m-%d-%H-%M-%S").lab4.sync; sleep 10; done' Enter
tmux send-key -t ${session_name}:1 'while true; do ~/bin/sync_client 195.148.127.234 > /tmp/webrtc/logs/sync/$(date +"%Y-%m-%d-%H-%M-%S").lab6.sync; sleep 10; done' Enter
tmux send-key -t ${session_name}:2 'cd ~/Workspace/eatw; python yolo_client.py $(cat /tmp/ns.ip)' Enter
tmux send-key -t ${session_name}:3 'cd ~/Workspace/eatw/containers/gps-sender; python sender.py' Enter
tmux send-key -t ${session_name}:4 'sudo gpsd /dev/ttyUSB0 -N' Enter
tmux send-key -t ${session_name}:6 'cd ~/Workspace/webrtc-controller/python_src; while 1; do python ping_client.py >> /tmp/webrtc/logs/ping.log &; sleep .1; done' Enter
tmux send-key -t ${session_name}:7 'cd ~/Workspace/webrtc-controller/python_src; python fake_edge_client.py > /tmp/webrtc/logs/edge_client.log' Enter
tmux send-key -t ${session_name}:5 '~/bin/peerconnection_client_headless --name SENDER --resolution 1920x1280 --server $(cat /tmp/ns.ip) --port 8881 > /tmp/webrtc/logs/client2.log 2>&1' Enter

