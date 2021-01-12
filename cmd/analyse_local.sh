#!/bin/zsh

source ~/.zshrc
conda activate dev
exp_name=webrtc_exp3
concurrency=12
weight=yolov5s
ls ~/Data/${exp_name} | xargs -P$concurrency -I FILE bash -c 'python -m analysis.main_local -d ~/Data/'${exp_name}'/FILE -w '$weight
#ls -d ~/Data/$exp_name/baseline_* | xargs -P$concurrency -I FILE bash -c 'python -m analysis.main_local -ad FILE -w '$weight

