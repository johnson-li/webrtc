#!/usr/bin/zsh

source ~/.zshrc
conda activate dev7
exp_name=webrtc_exp5
concurrency=11
weight=yolov5x
ls /mnt/wd/${exp_name} | xargs -P$concurrency -I FILE bash -c 'python -m analysis.main_local -d /mnt/wd/'${exp_name}'/FILE -w '$weight

