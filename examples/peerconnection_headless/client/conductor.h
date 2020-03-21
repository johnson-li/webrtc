/*
 *  Copyright 2012 The WebRTC Project Authors. All rights reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#ifndef EXAMPLES_PEERCONNECTION_CLIENT_CONDUCTOR_H_
#define EXAMPLES_PEERCONNECTION_CLIENT_CONDUCTOR_H_

#include <deque>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "api/media_stream_interface.h"
#include "api/peer_connection_interface.h"
#include "examples/peerconnection_headless/client/peer_connection_client.h"

namespace webrtc {
class VideoCaptureModule;
}  // namespace webrtc

namespace cricket {
class VideoRenderer;
}  // namespace cricket

class VideoRenderer : public rtc::VideoSinkInterface<webrtc::VideoFrame> {
 public:
  VideoRenderer(webrtc::VideoTrackInterface* track_to_render)
      : width_(0), height_(0), rendered_track_(track_to_render)  {
    rendered_track_->AddOrUpdateSink(this, rtc::VideoSinkWants());
  }

  ~VideoRenderer() {
    rendered_track_->RemoveSink(this);
  }

  void OnFrame(const webrtc::VideoFrame& frame) {
    // TODO: handle the video frame
  }

  const uint8_t* image() const { return image_.get(); }
  int width() const { return width_; }
  int height() const { return height_; }

 protected:
  void SetSize(int width, int height) {
    if (width_ == width && height_ == height) {
      return;
    }
    width_ = width;
    height_ = height;
    image_.reset(new uint8_t[width * height * 4]);
  }
  std::unique_ptr<uint8_t[]> image_;
  int width_;
  int height_;
  rtc::scoped_refptr<webrtc::VideoTrackInterface> rendered_track_;
};

class Conductor : public webrtc::PeerConnectionObserver,
                  public webrtc::CreateSessionDescriptionObserver,
                  public PeerConnectionClientObserver {
 public:
  enum CallbackID {
    MEDIA_CHANNELS_INITIALIZED = 1,
    PEER_CONNECTION_CLOSED,
    SEND_MESSAGE_TO_PEER,
    NEW_TRACK_ADDED,
    TRACK_REMOVED,
  };

  Conductor(PeerConnectionClient* client);

  bool connection_active() const;

  void Close();

  void StartLogin(const std::string& server, int port);

 protected:
  ~Conductor();
  bool InitializePeerConnection();
  bool ReinitializePeerConnectionForLoopback();
  bool CreatePeerConnection(bool dtls);
  void DeletePeerConnection();
  void EnsureStreamingUI();
  void AddTracks();
  void StartLocalRenderer(webrtc::VideoTrackInterface* local_video);
  void StopLocalRenderer();
  void StartRemoteRenderer(webrtc::VideoTrackInterface* remote_video);
  void StopRemoteRenderer();

  //
  // PeerConnectionObserver implementation.
  //

  void OnSignalingChange(
      webrtc::PeerConnectionInterface::SignalingState new_state) override {}
  void OnAddTrack(
      rtc::scoped_refptr<webrtc::RtpReceiverInterface> receiver,
      const std::vector<rtc::scoped_refptr<webrtc::MediaStreamInterface>>&
          streams) override;
  void OnRemoveTrack(
      rtc::scoped_refptr<webrtc::RtpReceiverInterface> receiver) override;
  void OnDataChannel(
      rtc::scoped_refptr<webrtc::DataChannelInterface> channel) override {}
  void OnRenegotiationNeeded() override {}
  void OnIceConnectionChange(
      webrtc::PeerConnectionInterface::IceConnectionState new_state) override {}
  void OnIceGatheringChange(
      webrtc::PeerConnectionInterface::IceGatheringState new_state) override {}
  void OnIceCandidate(const webrtc::IceCandidateInterface* candidate) override;
  void OnIceConnectionReceivingChange(bool receiving) override {}

  //
  // PeerConnectionClientObserver implementation.
  //

  void OnSignedIn() override;

  void OnDisconnected() override;

  void OnPeerConnected(int id, const std::string& name) override;

  void OnPeerDisconnected(int id) override;

  void OnMessageFromPeer(int peer_id, const std::string& message) override;

  void OnMessageSent(int err) override;

  void OnServerConnectionFailure() override;

  //
  // MainWndCallback implementation.
  //

  void DisconnectFromServer();

  void ConnectToPeer(int peer_id);

  void DisconnectFromCurrentPeer();

  void OperationCallback(int msg_id, void* data);

  // CreateSessionDescriptionObserver implementation.
  void OnSuccess(webrtc::SessionDescriptionInterface* desc) override;
  void OnFailure(webrtc::RTCError error) override;

 protected:
  // Send a message to the remote peer.
  void SendMessage(const std::string& json_object);

  int peer_id_;
  bool loopback_;
  rtc::scoped_refptr<webrtc::PeerConnectionInterface> peer_connection_;
  rtc::scoped_refptr<webrtc::PeerConnectionFactoryInterface>
      peer_connection_factory_;
  PeerConnectionClient* client_;
  std::deque<std::string*> pending_messages_;
  std::string server_;
  std::unique_ptr<VideoRenderer> local_renderer_;
  std::unique_ptr<VideoRenderer> remote_renderer_;
};

#endif  // EXAMPLES_PEERCONNECTION_CLIENT_CONDUCTOR_H_
