/*
 *  Copyright (c) 2016 The WebRTC project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include "media/engine/internal_encoder_factory.h"

#include <memory>
#include <string>
#include <vector>

#include "absl/strings/match.h"
#include "api/video_codecs/video_encoder_factory.h"
#include "api/video_codecs/video_encoder_factory_template.h"
#if defined(RTC_USE_LIBAOM_AV1_ENCODER)
#include "api/video_codecs/video_encoder_factory_template_libaom_av1_adapter.h"  // nogncheck
#endif
#include "api/video_codecs/video_encoder_factory_template_libvpx_vp8_adapter.h"
#include "api/video_codecs/video_encoder_factory_template_libvpx_vp9_adapter.h"
#if defined(WEBRTC_USE_H264)
#include "api/video_codecs/video_encoder_factory_template_open_h264_adapter.h"  // nogncheck
#include "api/video_codecs/video_encoder_factory_template_nvenc_h264_adapter.h"  // nogncheck
#endif

namespace webrtc {
namespace {

using Factory =
    VideoEncoderFactoryTemplate<webrtc::LibvpxVp8EncoderTemplateAdapter,
#if defined(WEBRTC_USE_H264)
                                webrtc::NvencH264EncoderTemplateAdapter,
                                // webrtc::OpenH264EncoderTemplateAdapter,
#endif
#if defined(RTC_USE_LIBAOM_AV1_ENCODER)
                                webrtc::LibaomAv1EncoderTemplateAdapter,
#endif
                                webrtc::LibvpxVp9EncoderTemplateAdapter>;

absl::optional<SdpVideoFormat> MatchOriginalFormat(
    const SdpVideoFormat& format) {
  const auto supported_formats = Factory().GetSupportedFormats();

  absl::optional<SdpVideoFormat> res;
  int best_parameter_match = 0;
  for (const auto& supported_format : supported_formats) {
    if (absl::EqualsIgnoreCase(supported_format.name, format.name)) {
      int matching_parameters = 0;
      for (const auto& kv : supported_format.parameters) {
        auto it = format.parameters.find(kv.first);
        if (it != format.parameters.end() && it->second == kv.second) {
          matching_parameters += 1;
        }
      }

      if (!res || matching_parameters > best_parameter_match) {
        res = supported_format;
        best_parameter_match = matching_parameters;
      }
    }
  }

  return res;
}
}  // namespace

std::vector<SdpVideoFormat> InternalEncoderFactory::GetSupportedFormats()
    const {
  return Factory().GetSupportedFormats();
}

std::unique_ptr<VideoEncoder> InternalEncoderFactory::CreateVideoEncoder(
    const SdpVideoFormat& format) {
  auto original_format = MatchOriginalFormat(format);
  return original_format ? Factory().CreateVideoEncoder(*original_format)
                         : nullptr;
}

VideoEncoderFactory::CodecSupport InternalEncoderFactory::QueryCodecSupport(
    const SdpVideoFormat& format,
    absl::optional<std::string> scalability_mode) const {
  auto original_format = MatchOriginalFormat(format);
  return original_format
             ? Factory().QueryCodecSupport(*original_format, scalability_mode)
             : VideoEncoderFactory::CodecSupport{.is_supported = false};
}

}  // namespace webrtc
