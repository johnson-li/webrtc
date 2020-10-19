#!/bin/bash

cd ~/Workspace/yolov5
for f in ~/Data/webrtc/*
do
    python -m stream_local -p $f/dump
done

cd ~/Workspace/webrtc-controller
for f in ~/Data/webrtc/*
do
    python -m analysis.main_local -d $f
done
