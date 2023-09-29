/*
 *  Copyright 2012 The WebRTC Project Authors. All rights reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#ifndef EXAMPLES_PEERCONNECTION_PANDIA_FLAG_DEFS_H_
#define EXAMPLES_PEERCONNECTION_PANDIA_FLAG_DEFS_H_

#include <string>

#include "absl/flags/flag.h"

ABSL_FLAG(std::string, path, "/home/lix16/Downloads", "The folder of the input video files.");
ABSL_FLAG(std::string, obs_socket, "", "The IPC socket of the observer");
ABSL_FLAG(std::string, dump_path, "", "The folder of dumping received video frames.");
ABSL_FLAG(std::string, logging_path, "", "The name of the logging file.");
ABSL_FLAG(std::string, shm_name, "pandia", "The name of the shared memory.");
ABSL_FLAG(int, resolution, 1080, "The capture height of the video frame.");
ABSL_FLAG(int, fps, 30, "The capture FPS of the video frame.");
ABSL_FLAG(std::string, force_fieldtrials,
    "",
    "Field trials control experimental features. This flag specifies the field "
    "trials in effect. E.g. running with "
    "--force_fieldtrials=WebRTC-FooFeature/Enabled/ "
    "will assign the group Enabled to field trial WebRTC-FooFeature. Multiple "
    "trials are separated by \"/\"");
#endif  // EXAMPLES_PEERCONNECTION_CLIENT_FLAG_DEFS_H_
