./sync_data.sh
ssh lab6 'bash -s' < start_experiment_remote.sh

sleep 3

echo 'Starting local client'
./data/peerconnection_client_headless --server 195.148.127.108 --logger data/client2.logb > data/client2.log 2>&1

