import os
import json
import matplotlib.pyplot as plt
import numpy as np


def main():
    folder = "/home/johnson/Data/webrtc/results"
    records = []
    for i in range(1, 100):
        if not os.path.exists(os.path.join(folder, f'logs{i}')):
            continue
        file_name = f'logs{i}/analysis_latency.txt'
        file_name2 = f'logs{i}/metadata.txt'
        file_path = os.path.join(folder, file_name)
        file_path2 = os.path.join(folder, file_name2)
        with open(file_path, 'r') as f:
            skip = True
            buffer = ""
            for line in f.readlines():
                line = line.strip()
                if line.startswith("'============"):
                    skip = False
                    continue
                if skip:
                    continue
                buffer += line
            buffer = buffer.replace("'", '"')
            data = json.loads(buffer)
        with open(file_path2, 'r') as f:
            metadata = {}
            for line in f.readlines():
                line = line.strip()
                if line:
                    sp = line.split('=')
                    metadata[sp[0]] = sp[1]
        records.append({'metadata': metadata, 'statics': data})
    records_h264 = list(filter(lambda x: x['metadata']['codec'] == 'h264', records))
    records_vp8 = list(filter(lambda x: x['metadata']['codec'] == 'vp8', records))
    x1 = np.array([int(r['metadata']['bitrate']) for r in records_h264])
    x2 = np.array([int(r['metadata']['bitrate']) for r in records_vp8])
    i1 = np.argsort(x1)
    i2 = np.argsort(x2)
    statics = 'med'
    decoding1 = np.array([float(r['statics']['decoding_latency'][statics]) for r in records_h264])
    encoding1 = np.array([float(r['statics']['encoding_latency'][statics]) for r in records_h264])
    decoding2 = np.array([float(r['statics']['decoding_latency'][statics]) for r in records_vp8])
    encoding2 = np.array([float(r['statics']['encoding_latency'][statics]) for r in records_vp8])
    size1 = np.array([float(r['statics']['encoded_size (kb)'][statics]) for r in records_h264])
    size2 = np.array([float(r['statics']['encoded_size (kb)'][statics]) for r in records_vp8])
    transmission1 = np.array([float(r['statics']['frame_transmission_latency'][statics]) for r in records_h264])
    transmission2 = np.array([float(r['statics']['frame_transmission_latency'][statics]) for r in records_vp8])

    plt.rcParams.update({'font.size': 16})
    plt.figure(figsize=(10, 6))
    plt.title("Encoding and decoding latency")
    plt.plot(x1[i1], decoding1[i1])
    plt.plot(x1[i1], encoding1[i1])
    plt.plot(x2[i2], decoding2[i2], linestyle='-.')
    plt.plot(x2[i2], encoding2[i2], linestyle='-.')
    plt.ylabel("Latency (ms)")
    plt.xlabel("Bitrate (kbps)")
    plt.legend(["H264 - Decoding", "H264 - Encoding", "VP8 - Decoding", "VP8 - Encoding"])
    plt.savefig('latency_bitrate.png', dpi=600)
    plt.show()

    fig, ax1 = plt.subplots(figsize=(10, 6))
    color1 = 'tab:red'
    color2 = 'tab:blue'
    plt.title("Encoded size and transmission latency")
    ax1.set_xlabel('Bitrate (kbps)')
    ax1.set_ylabel('Encoded size (KB)', color=color1)
    ax1.plot(x1[i1], size1[i1], color=color1)
    ax1.plot(x2[i2], size2[i2], color=color1, linestyle='-.')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax2 = ax1.twinx()
    ax2.set_ylabel('Transmission latency (ms)', color=color2)
    ax2.plot(x1[i1], transmission1[i1], color=color2)
    ax2.plot(x2[i2], transmission2[i2], color=color2, linestyle='-.')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax1.legend(['H264', 'VP8'])
    fig.tight_layout()
    plt.savefig('encoded_size_bitrate.png', dpi=600)
    plt.show()


if __name__ == '__main__':
    main()
