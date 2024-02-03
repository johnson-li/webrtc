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
#include <fstream>

#include "api/media_stream_interface.h"
#include "api/peer_connection_interface.h"
#include "examples/peerconnection_headless/client/peer_connection_client.h"
#include "rtc_base/thread.h"

namespace webrtc {
class VideoCaptureModule;
}  // namespace webrtc

namespace cricket {
class VideoRenderer;
}  // namespace cricket

class cricket::VideoRenderer : public rtc::VideoSinkInterface<webrtc::VideoFrame> {
  public:
   VideoRenderer(std::string name, webrtc::VideoTrackInterface* track_to_render)
       : name_(name), width_(0), height_(0), 
       shared_frames_(nullptr), rendered_track_(track_to_render)  {
     rendered_track_->AddOrUpdateSink(this, rtc::VideoSinkWants());
     if (name_ == "remote") {
    //    initSharedMemory();
     }
   }

   ~VideoRenderer() {
     rendered_track_->RemoveSink(this);
   }

   void OnFrame(const webrtc::VideoFrame& frame) {
      if (dump_path_.size() > 1) {
        std::ostringstream filename;
        filename << dump_path_ << "/received_" << frame.first_rtp_sequence << ".yuv";
        std::ofstream wf(filename.str(), std::ios::out | std::ios::binary);
        if (!wf) {
          RTC_INFO << "Failed to open the dumping file";
          return;
        }
        int size = frame.width() * frame.height() * 3 / 2;
        uint8_t* data = new uint8_t[size];
        memcpy(data, frame.video_frame_buffer()->GetI420()->DataY(), frame.width() * frame.height());
        memcpy(data + frame.width() * frame.height(), frame.video_frame_buffer()->GetI420()->DataU(), 
            frame.width() * frame.height() / 4);
        memcpy(data + frame.width() * frame.height() * 5 / 4, frame.video_frame_buffer()->GetI420()->DataV(), 
            frame.width() * frame.height() / 4);
        wf.write((char*)data, size);
        wf.close();
        RTC_INFO << "Dump to " << filename.str() << ", " << 
            frame.width() << "x" << frame.height();
      }
   }

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
   std::string name_;
   int width_;
   int height_;
   std::string dump_path_;
   struct shared_frames* shared_frames_;
   unsigned char* shared_memory_;
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

  Conductor(PeerConnectionClient* client, bool receiving_only, 
            uint32_t width, uint32_t fps, std::string path, std::string dump_path);

  bool connection_active() const;

  void Close();

  void ConnectToPeer(int peer_id) override;

 protected:
  ~Conductor();
  bool InitializePeerConnection();
  bool ReinitializePeerConnectionForLoopback();
  bool CreatePeerConnection();
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

  void OnMessageFromPeer(int peer_id, const std::string& message) override;
  void OnMessageFromPeerOnNextIter(int peer_id, const std::string& message);


  void OnMessageSent(int err) override;

  void OnServerConnectionFailure() override;

  void OperationCallback(int msg_id, void* data);

  // CreateSessionDescriptionObserver implementation.
  void OnSuccess(webrtc::SessionDescriptionInterface* desc) override;
  void OnFailure(webrtc::RTCError error) override;

 protected:
  // Send a message to the remote peer.
  void SendMessage(const std::string& json_object);

  int peer_id_;
  int remote_peer_;
  uint32_t width_;
  uint32_t fps_;
  bool loopback_;
  bool receiving_only_;
  bool connected_;
  bool flag_;
  std::string path_;
  std::string dump_path_;
  std::unique_ptr<rtc::Thread> signaling_thread_;
  rtc::scoped_refptr<webrtc::PeerConnectionInterface> peer_connection_;
  rtc::scoped_refptr<webrtc::PeerConnectionFactoryInterface>
      peer_connection_factory_;
  PeerConnectionClient* client_;
  std::deque<std::string*> pending_messages_;
  std::string server_;
  std::unique_ptr<cricket::VideoRenderer> local_renderer_;
  std::unique_ptr<cricket::VideoRenderer> remote_renderer_;
};

#endif  // EXAMPLES_PEERCONNECTION_CLIENT_CONDUCTOR_H_