#!/bin/bash

mv /tmp/webrtc/logs /tmp/webrtc/$(date)logs
mkdir -p /tmp/webrtc/logs/frames1
mkdir -p /tmp/webrtc/logs/frames2
mkdir -p /tmp/webrtc/logs/frames3
mkdir -p /tmp/webrtc/logs/frames4
mkdir -p /tmp/webrtc/logs/frames5


session_name=dns
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
tmux send-key -t ${session_name}:0 'cd ~; conda activate dev' Enter
for i in $(seq 4); do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'cd ~; conda activate dev' Enter
done
# tmux send-key -t ${session_name}:0 'python -m dns.monitor_client --name fi --region ES' Enter
tmux send-key -t ${session_name}:1 'authbind python -m dns.resolver > /tmp/webrtc/logs/$(date +"%Y-%m-%d-%H-%M-%S").dns.log' Enter


session_name=mobix
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
tmux send-key -t ${session_name}:0 'cd ~; conda activate dev' Enter
for i in $(seq 4); do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'cd ~; conda activate dev' Enter
done
tmux send-key -t ${session_name}:0 'while true; do ./bin/sync_server; done' Enter
tmux send-key -t ${session_name}:1 './bin/peerconnection_server_headless --port 8881' Enter
tmux send-key -t ${session_name}:2 './bin/peerconnection_client_headless --receiving_only --name RECEIVER --dump /tmp/webrtc/logs/frames1 --server 127.0.0.1 --port 8881 > /tmp/webrtc/logs/client1.1.log 2>&1' Enter
