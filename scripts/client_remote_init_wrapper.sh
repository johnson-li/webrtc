#!/bin/bash

DIR=`dirname "$(realpath $0)"`

session_name=init
tmux has-session -t ${session_name} 2> /dev/null; if [[ $? == 0 ]]; then tmux kill-session -t ${session_name}; fi
tmux new-session -ds ${session_name}
#for i in `seq 1`; do
#    tmux new-window -t ${session_name}:$i
#done

tmux send-key -t ${session_name}:0 "${DIR}/client_remote_init.sh" Enter

