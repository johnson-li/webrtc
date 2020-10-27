#!/bin/bash

exp_name=webrtc_exp5
ls /mnt/wd/$exp_name | xargs -P8 -I FILE bash -c 'python -m analysis.main_local -d /mnt/wd/'$exp_name'/FILE'

