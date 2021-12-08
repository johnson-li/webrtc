#!/bin/bash

rm -r /tmp/webrtc/logs
mkdir -p /tmp/webrtc/logs/frames1
mkdir -p /tmp/webrtc/logs/frames2
mkdir -p /tmp/webrtc/logs/frames3
mkdir -p /tmp/webrtc/logs/frames4
mkdir -p /tmp/webrtc/logs/frames5

session_name=mobix
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
tmux send-key -t ${session_name}:0 'cd ~; conda activate dev' Enter
for i in $(seq 12); do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'cd ~; conda activate dev' Enter
done

tmux send-key -t ${session_name}:0 'while true; do ./bin/sync_server; done' Enter
tmux send-key -t ${session_name}:1 './bin/peerconnection_server_headless --port 8881' Enter
tmux send-key -t ${session_name}:2 './bin/peerconnection_server_headless --port 8882' Enter
tmux send-key -t ${session_name}:3 './bin/peerconnection_server_headless --port 8883' Enter
tmux send-key -t ${session_name}:4 './bin/peerconnection_server_headless --port 8884' Enter
tmux send-key -t ${session_name}:5 './bin/peerconnection_server_headless --port 8885' Enter
tmux send-key -t ${session_name}:6 './bin/peerconnection_client_headless --receiving_only --name RECEIVER --dump /tmp/webrtc/logs/frames1 --server 127.0.0.1 --port 8881 > /tmp/webrtc/logs/client1.1.log 2>&1' Enter
tmux send-key -t ${session_name}:7 './bin/peerconnection_client_headless --receiving_only --name RECEIVER --dump /tmp/webrtc/logs/frames2 --server 127.0.0.1 --port 8882 > /tmp/webrtc/logs/client1.2.log 2>&1' Enter
tmux send-key -t ${session_name}:8 './bin/peerconnection_client_headless --receiving_only --name RECEIVER --dump /tmp/webrtc/logs/frames3 --server 127.0.0.1 --port 8883 > /tmp/webrtc/logs/client1.3.log 2>&1' Enter
tmux send-key -t ${session_name}:9 './bin/peerconnection_client_headless --receiving_only --name RECEIVER --dump /tmp/webrtc/logs/frames4 --server 127.0.0.1 --port 8884 > /tmp/webrtc/logs/client1.4.log 2>&1' Enter
tmux send-key -t ${session_name}:10 './bin/peerconnection_client_headless --receiving_only --name RECEIVER --dump /tmp/webrtc/logs/frames5 --server 127.0.0.1 --port 8885 > /tmp/webrtc/logs/client1.5.log 2>&1' Enter
