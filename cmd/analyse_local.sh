#!/bin/zsh

source ~/.zshrc
conda activate dev
exp_name=webrtc_exp3
concurrency=12
weight=yolov5x
ls ~/Data/${exp_name} | xargs -P$concurrency -I FILE bash -c 'python -m analysis.main_local -d ~/Data/'${exp_name}'/FILE -w '$weight

