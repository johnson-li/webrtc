/*
 *  Copyright 2012 The WebRTC Project Authors. All rights reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#ifndef EXAMPLES_PEERCONNECTION_CLIENT_FLAG_DEFS_H_
#define EXAMPLES_PEERCONNECTION_CLIENT_FLAG_DEFS_H_

#include <string>

#include "absl/flags/flag.h"

extern const uint16_t kDefaultServerPort;  // From defaults.[h|cc]

// Define flags for the peerconnect_client testing tool, in a separate
// header file so that they can be shared across the different main.cc's
// for each platform.

ABSL_FLAG(bool,
          autoconnect,
          false,
          "Connect to the server without user "
          "intervention.");
ABSL_FLAG(std::string, server, "127.0.0.1", "The server to connect to.");
ABSL_FLAG(std::string, path, "/home/lix16/Downloads", "The folder of the input video files.");
ABSL_FLAG(std::string, obs_socket, "", "The IPC socket of the observer");
ABSL_FLAG(std::string, dump_path, "", "The folder of dumping received video frames.");
ABSL_FLAG(std::string, logging_path, "", "The name of the logging file.");
ABSL_FLAG(int,
          port,
          kDefaultServerPort,
          "The port on which the server is listening.");
ABSL_FLAG(int,
          width,
          1080,
          "The capture width of the video frame.");
ABSL_FLAG(int,
          fps,
          30,
          "The capture FPS of the video frame.");
ABSL_FLAG(
    bool,
    autocall,
    false,
    "Call the first available other client on "
    "the server without user intervention.  Note: this flag should only be set "
    "to true on one of the two clients.");
ABSL_FLAG(
    bool,
    receiving_only,
    false,
    "Make the peer as a receiver only");
ABSL_FLAG(
    std::string,
    force_fieldtrials,
    "",
    "Field trials control experimental features. This flag specifies the field "
    "trials in effect. E.g. running with "
    "--force_fieldtrials=WebRTC-FooFeature/Enabled/ "
    "will assign the group Enabled to field trial WebRTC-FooFeature. Multiple "
    "trials are separated by \"/\"");
ABSL_FLAG(
    std::string,
    resolution,
    "",
    "Specify a static resolution at the sender, e.g., 1920x1280. If this parameter is set, "
    "the cricket::VideoAdapter will never try to scale down the frames.");
ABSL_FLAG(
    std::string,
    name,
    "client_default",
    "Specify the peer name of the client.");

#endif  // EXAMPLES_PEERCONNECTION_CLIENT_FLAG_DEFS_H_