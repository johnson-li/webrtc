#!/usr/bin/env bash

SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

cd $SCRIPTPATH
cd ../
ninja -C out/Default > /dev/null

./out/Default/peerconnection_server_headless > experiment/server.log 2>&1 &
server_pid=$!
echo "server pid: ${server_pid}"
sleep .3

./out/Default/peerconnection_client_headless --logger experiment/client1.logb > experiment/client1.log 2>&1 &
client1_pid=$!
echo "client1 pid: ${client1_pid}"
sleep .3

./out/Default/peerconnection_client_headless --logger experiment/client2.logb > experiment/client2.log 2>&1 &
client2_pid=$!
echo "client2 pid: ${client2_pid}"

echo 'Wait 5 seconds for experiment...'
sleep 5

kill -s SIGINT ${client1_pid}
kill -s SIGINT ${client2_pid}
kill ${server_pid}

