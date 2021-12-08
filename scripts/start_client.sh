#!/bin/bash

mv /tmp/webrtc/logs "/tmp/webrtc/$(date).logs"
mkdir -p /tmp/webrtc/logs/yolo
mkdir -p /tmp/webrtc/logs/gps

session_name=mobix
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
tmux send-key -t ${session_name}:0 'cd ~; conda activate dev' Enter
for i in $(seq 6); do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'cd ~; conda activate dev' Enter
done
tmux send-key -t ${session_name}:0 'while true; do ./bin/sync_client 195.148.127.233 > /tmp/webrtc/logs/sync/$(date +"%Y-%m-%d-%H-%M-%S").lab4.sync; sleep 10; done' Enter
tmux send-key -t ${session_name}:1 'while true; do ./bin/sync_client 195.148.127.234 > /tmp/webrtc/logs/sync/$(date +"%Y-%m-%d-%H-%M-%S").lab6.sync; sleep 10; done' Enter
tmux send-key -t ${session_name}:2 'cd ~/Workspace/eatw; python yolo_client.py' Enter
tmux send-key -t ${session_name}:3 'cd ~/Workspace/eatw/containers/gps-sender; python sender.py' Enter

