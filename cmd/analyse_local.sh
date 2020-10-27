#!/usr/bin/zsh

source ~/.zshrc
conda activate dev7
exp_name=webrtc_exp5
ls /mnt/wd/$exp_name | xargs -P8 -I FILE bash -c 'python -m analysis.main_local -d /mnt/wd/'$exp_name'/FILE -w yolov5s'

