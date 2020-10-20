#!/bin/bash

ls ~/Data/webrtc-exp1 | xargs -P0 -I FILE bash -c 'python -m analysis.main_local -d ~/Data/webrtc-exp1/FILE'

