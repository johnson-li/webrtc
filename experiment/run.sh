#!/usr/bin/env bash

SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

cd $SCRIPTPATH
cd ../
ninja -C out/Default > /dev/null

./out/Default/peerconnection_client_headless > experiment/experiment.client1.log 2>&1 &
sleep 1
./out/Default/peerconnection_client_headless > experiment/experiment.client2.log 2>&1 &

echo 'Wait 5 seconds for experiment...'
sleep 5
killall -s SIGINT peerconnection_client_headless

