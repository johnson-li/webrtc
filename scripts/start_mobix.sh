#!/bin/bash

session_name=mobix
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
tmux send-key -t ${session_name}:0 'conda activate dev' Enter
for i in $(seq 8); do
    tmux new-window -t ${session_name}:$i
    tmux send-key -t ${session_name}:$i 'conda activate dev' Enter
done

tmux send-key -t ${session_name}:0 'while true; do ./bin/sync_server; done' Enter
