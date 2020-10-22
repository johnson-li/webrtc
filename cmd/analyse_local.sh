#!/bin/bash

exp_name=webrtc-exp2
ls ~/Data/$exp_name | xargs -P0 -I FILE bash -c 'python -m analysis.main_local -d ~/Data/'$exp_name'/FILE'

