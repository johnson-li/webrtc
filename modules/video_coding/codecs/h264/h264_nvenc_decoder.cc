/*
 *  Copyright (c) 2015 The WebRTC project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 *
 */

// Everything declared/defined in this header is only required when WebRTC is
// build with H264 support, please do not move anything out of the
// #ifdef unless needed and tested.
#ifdef WEBRTC_USE_H264

#include "modules/video_coding/codecs/h264/h264_nvenc_decoder.h"

#include <algorithm>
#include <limits>
#include <memory>

#include "api/video/i010_buffer.h"
#include "api/video/i420_buffer.h"
#include "common_video/include/video_frame_buffer.h"
#include "rtc_base/checks.h"
#include "rtc_base/logging.h"
#include "system_wrappers/include/field_trial.h"
#include "system_wrappers/include/metrics.h"
#include "third_party/libyuv/include/libyuv/convert.h"
#include "cuviddec.h"
#include "NvDecoder.h"

namespace webrtc {

namespace {

// const size_t kYPlaneIndex = 0;
// const size_t kUPlaneIndex = 1;
// const size_t kVPlaneIndex = 2;

}  // namespace

enum H264DecoderImplEvent {
  kH264DecoderEventInit = 0,
  kH264DecoderEventError = 1,
  kH264DecoderEventMax = 16,
};

H264NvDecoder::H264NvDecoder()
    : decoded_image_callback_(nullptr),
      has_reported_init_(false),
      has_reported_error_(false),
      preferred_output_format_(field_trial::IsEnabled("WebRTC-NV12Decode")
                                   ? VideoFrameBuffer::Type::kNV12
                                   : VideoFrameBuffer::Type::kI420) {}

H264NvDecoder::~H264NvDecoder() {
  Release();
}

bool H264NvDecoder::Configure(const Settings& settings) {
  ReportInit();
  if (settings.codec_type() != kVideoCodecH264) {
    ReportError();
    return false;
  }

  // Release necessary in case of re-initializing.
  int32_t ret = Release();
  if (ret != WEBRTC_VIDEO_CODEC_OK) {
    ReportError();
    return false;
  }

  // Init cuda context
  CUcontext cuContext = NULL;
  CUdevice cuDevice = 0;
  for (int gpu_index = 1; gpu_index >= 0; gpu_index--) {
    auto result = cuDeviceGet(&cuDevice, gpu_index);
    if (result == CUDA_SUCCESS) {
      result = cuCtxCreate(&cuContext, 0, cuDevice);
      if (result == CUDA_SUCCESS) {
        RTC_INFO << "Created CUDA context for GPU " << gpu_index;
        break;
      }
    }
  }
  if (cuContext == NULL) {
    RTC_INFO << "Failed to create CUDA context.";
    ReportError();
    return false;
  } 
  Rect cropRect = {};
  Dim resizeDim = {};

  RTC_DCHECK(!decoder_);
  decoder_.reset(new NvDecoder(cuContext, false, cudaVideoCodec_H264, false, 
                               false, &cropRect, &resizeDim, false));
  int opPoint = 0;
  bool bDispAllLayers = false;
  decoder_->SetOperatingPoint(opPoint, bDispAllLayers);
  return true;
}

int32_t H264NvDecoder::Release() {
  decoder_.reset();
  return WEBRTC_VIDEO_CODEC_OK;
}

int32_t H264NvDecoder::RegisterDecodeCompleteCallback(
    DecodedImageCallback* callback) {
  decoded_image_callback_ = callback;
  return WEBRTC_VIDEO_CODEC_OK;
}

int32_t H264NvDecoder::Decode(const EncodedImage& input_image,
                                bool /*missing_frames*/,
                                int64_t /*render_time_ms*/) {
  if (!IsInitialized()) {
    ReportError();
    return WEBRTC_VIDEO_CODEC_UNINITIALIZED;
  }
  if (!decoded_image_callback_) {
    RTC_LOG(LS_WARNING)
        << "Configure() has been called, but a callback function "
           "has not been set with RegisterDecodeCompleteCallback()";
    ReportError();
    return WEBRTC_VIDEO_CODEC_UNINITIALIZED;
  }
  if (!input_image.data() || !input_image.size()) {
    ReportError();
    return WEBRTC_VIDEO_CODEC_ERR_PARAMETER;
  }

  int nFrameReturned = decoder_->Decode(input_image.data(), input_image.size());
  RTC_INFO << "Decoded " << nFrameReturned << " frames";
  // TODO: Continue here

  return WEBRTC_VIDEO_CODEC_OK;
}

const char* H264NvDecoder::ImplementationName() const {
  return "nvdec";
}

bool H264NvDecoder::IsInitialized() const {
  return decoder_ != nullptr;
}

void H264NvDecoder::ReportInit() {
  if (has_reported_init_)
    return;
  RTC_HISTOGRAM_ENUMERATION("WebRTC.Video.H264NvDecoder.Event",
                            kH264DecoderEventInit, kH264DecoderEventMax);
  has_reported_init_ = true;
}

void H264NvDecoder::ReportError() {
  if (has_reported_error_)
    return;
  RTC_HISTOGRAM_ENUMERATION("WebRTC.Video.H264NvDecoder.Event",
                            kH264DecoderEventError, kH264DecoderEventMax);
  has_reported_error_ = true;
}

}  // namespace webrtc

#endif  // WEBRTC_USE_H264
