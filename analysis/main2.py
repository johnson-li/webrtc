import os
import json


def main():
    folder = "/home/lix16/Workspace/webrtc/src/results"
    records = []
    for i in range(1, 15):
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
            data = json.loads(buffer)
        with open(file_path2, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                metadata = {}
                if line:
                    sp = line.split('=')
                    metadata[sp[0]] = sp[1]
        records.append({'metadata': metadata, 'statics': data})


if __name__ == '__main__':
    main()
