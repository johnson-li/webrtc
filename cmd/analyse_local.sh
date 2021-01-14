#!/bin/zsh

source ~/.zshrc
conda activate dev
exp_name=webrtc_exp3
pat=~/Data/${exp_name}
pat=~/Data/webrtc_exp3_mobix/webrtc_exp3
concurrency=12
weight=yolov5s
ls ${pat} | xargs -P$concurrency -I FILE bash -c 'python -m analysis.main_local -d '${pat}'/FILE -w '$weight
#ls -d ~/Data/$exp_name/baseline_* | xargs -P$concurrency -I FILE bash -c 'python -m analysis.main_local -ad FILE -w '$weight

