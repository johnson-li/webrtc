#!/bin/bash

rm -r /tmp/webrtc/logs
mkdir -p /tmp/webrtc/logs/gps


session_name=dns
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
tmux send-key -t ${session_name}:0 'conda activate dev' Enter
for i in $(seq 4); do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'conda activate dev' Enter
done
tmux send-key -t ${session_name}:0 'authbind python -m dns.server > /tmp/webrtc/logs/$(date +"%Y-%m-%d-%H-%M-%S").dns.log' Enter
tmux send-key -t ${session_name}:1 'python -m dns.monitor_server' Enter


session_name=mobix
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
tmux send-key -t ${session_name}:0 'conda activate dev' Enter
for i in $(seq 8); do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'conda activate dev' Enter
done
tmux send-key -t ${session_name}:0 'while true; do ./bin/sync_server; done' Enter
tmux send-key -t ${session_name}:1 'cd ~/Workspace/eatw/containers/gps-sender; python receiver.py' Enter

