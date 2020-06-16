#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
CONDA_ENV7=webrtc-exp7
CONDA_ENV8=webrtc-exp8

sudo modprobe v4l2loopback

conda env list| grep ${CONDA_ENV7} > /dev/null
if [[ $? == 1 ]]
then
    conda create -n ${CONDA_ENV7} python=3.7 -y > /dev/null
fi
conda env list| grep ${CONDA_ENV8} > /dev/null
if [[ $? == 1 ]]
then
    conda create -n ${CONDA_ENV8} python=3.8 -y > /dev/null
fi

conda activate ${CONDA_ENV8}
pip install -r /tmp/webrtc/yolo/requirements.txt > /dev/null
conda activate ${CONDA_ENV7}
pip install -r /tmp/webrtc/python_src/requirements.txt > /dev/null

