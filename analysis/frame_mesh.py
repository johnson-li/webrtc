import argparse
import os
import numpy as np
from multiprocessing import Pool
from analysis.illustrator_mesh import get_meta
from analysis.frame import handle_frame0, load_caches
from analysis.parser import parse_results_accuracy
from analysis.main import get_results_accuracy
import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser(description='A tool for visualization in a heatmap.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp9'), help='Data directory')
    args = parser.parse_args()
    return args


def normalized(a):
    min_a = min(a)
    max_a = max(a)
    a = np.array(a)
    return (a - min_a) / (max_a - min_a)


def illustrate():
    baseline = {'mAP': [0.4721483103140973, 0.568125532086497],
                'sharpness': [114.10812989191997, 113.98667774570598],
                'contrast': [56.41311732567193, 56.410936394345406]}

    data_1920_yolov5s = [
        {'bitrate': '500', 'mAP': 0.35416431834410544, 'sharpness': 135.11802049755576, 'contrast': 60.672957958698554},
        {'bitrate': '1000', 'mAP': 0.3845808569164617, 'sharpness': 107.40676041912793, 'contrast': 62.20434015843233},
        {'bitrate': '1500', 'mAP': 0.4347775125722245, 'sharpness': 117.27781172301371, 'contrast': 62.45690073785249},
        {'bitrate': '2000', 'mAP': 0.4476506151100408, 'sharpness': 121.98015759544745, 'contrast': 62.67329530233029},
        {'bitrate': '2500', 'mAP': 0.4627952132190798, 'sharpness': 127.8585052824888, 'contrast': 62.59183570376822},
        {'bitrate': '3500', 'mAP': 0.48026399568367983, 'sharpness': 131.4842112015621, 'contrast': 62.613898167703866},
        {'bitrate': '4000', 'mAP': 0.4828407986237899, 'sharpness': 133.09098335784228, 'contrast': 62.743062047715085},
        {'bitrate': '4500', 'mAP': 0.4883549698715618, 'sharpness': 136.87536598897546, 'contrast': 62.784653337932696},
        {'bitrate': '5000', 'mAP': 0.4884877039311074, 'sharpness': 138.5134646421183, 'contrast': 62.74698842695032},
        {'bitrate': '5500', 'mAP': 0.4896621847286934, 'sharpness': 138.05496432276513, 'contrast': 62.753146584356664},
        {'bitrate': '6000', 'mAP': 0.4911457876719653, 'sharpness': 143.23627813378832, 'contrast': 62.66634052236511},
        {'bitrate': '7000', 'mAP': 0.4946909518513012, 'sharpness': 135.08568754290047, 'contrast': 62.85007688664858},
        {'bitrate': '8000', 'mAP': 0.4984503750944156, 'sharpness': 149.10872875409805, 'contrast': 62.7878893326954},
        {'bitrate': '9000', 'mAP': 0.4935750191617705, 'sharpness': 161.111903060731, 'contrast': 63.59850127151203},
        {'bitrate': '10000', 'mAP': 0.3440309557575266, 'sharpness': 163.9495567544371, 'contrast': 63.74681561345141},
    ]
    data_1920_yolov5x = [
        {'bitrate': '500', 'mAP': 0.41097143088793425, 'sharpness': 135.11802049755576, 'contrast': 60.672957958698554},
        {'bitrate': '1000', 'mAP': 0.4529023468460017, 'sharpness': 107.40676041912793, 'contrast': 62.20434015843233},
        {'bitrate': '1500', 'mAP': 0.4990079780860308, 'sharpness': 117.27781172301371, 'contrast': 62.45690073785249},
        {'bitrate': '2000', 'mAP': 0.5220124279204329, 'sharpness': 121.98015759544745, 'contrast': 62.67329530233029},
        {'bitrate': '2500', 'mAP': 0.5352253231306388, 'sharpness': 127.8585052824888, 'contrast': 62.59183570376822},
        {'bitrate': '3500', 'mAP': 0.5582912706182154, 'sharpness': 131.4842112015621, 'contrast': 62.613898167703866},
        {'bitrate': '4000', 'mAP': 0.5557262638058522, 'sharpness': 133.09098335784228, 'contrast': 62.743062047715085},
        {'bitrate': '4500', 'mAP': 0.5627039790511466, 'sharpness': 136.87536598897546, 'contrast': 62.784653337932696},
        {'bitrate': '5000', 'mAP': 0.5684053310084918, 'sharpness': 138.5134646421183, 'contrast': 62.74698842695032},
        {'bitrate': '5500', 'mAP': 0.5657150717039094, 'sharpness': 138.05496432276513, 'contrast': 62.753146584356664},
        {'bitrate': '6000', 'mAP': 0.5665039101493182, 'sharpness': 143.23627813378832, 'contrast': 62.66634052236511},
        {'bitrate': '7000', 'mAP': 0.5712444330441206, 'sharpness': 135.08568754290047, 'contrast': 62.85007688664858},
        {'bitrate': '8000', 'mAP': 0.5703264143590562, 'sharpness': 149.10872875409805, 'contrast': 62.7878893326954},
        {'bitrate': '9000', 'mAP': 0.5607400979020415, 'sharpness': 161.111903060731, 'contrast': 63.59850127151203},
        {'bitrate': '10000', 'mAP': 0.5651374350158047, 'sharpness': 163.9495567544371, 'contrast': 63.74681561345141},
    ]
    data_1680_yolov5x = [
        {'bitrate': '500', 'mAP': 0.4018506920653605, 'sharpness': 99.90232177030998, 'contrast': 58.041528424191505},
        {'bitrate': '1000', 'mAP': 0.47422815091310866, 'sharpness': 79.87281104183715, 'contrast': 59.50342120210514},
        {'bitrate': '1500', 'mAP': 0.5054729078499665, 'sharpness': 85.12458261711976, 'contrast': 59.17485795482186},
        {'bitrate': '2000', 'mAP': 0.5207979986097864, 'sharpness': 93.88755238525415, 'contrast': 59.2322245261167},
        {'bitrate': '2500', 'mAP': 0.5301392741863445, 'sharpness': 98.20473351815167, 'contrast': 59.42353048116412},
        {'bitrate': '3000', 'mAP': 0.5363559192758377, 'sharpness': 102.82838159645375, 'contrast': 59.56600243608433},
        {'bitrate': '3500', 'mAP': 0.5425052582451347, 'sharpness': 102.84523359329793, 'contrast': 59.31474844551592},
        {'bitrate': '4000', 'mAP': 0.5411801347728158, 'sharpness': 103.1384289573714, 'contrast': 59.19617041344503},
        {'bitrate': '4500', 'mAP': 0.54527699845466, 'sharpness': 106.46893313482744, 'contrast': 59.61812952455157},
        {'bitrate': '5000', 'mAP': 0.5476106200740584, 'sharpness': 106.17390516193248, 'contrast': 59.44949518061699},
        {'bitrate': '5500', 'mAP': 0.5514568361103873, 'sharpness': 107.08840240058079, 'contrast': 59.284397330423744},
        {'bitrate': '6000', 'mAP': 0.5534263560386545, 'sharpness': 106.13736779979097, 'contrast': 59.3136323274593},
        {'bitrate': '7000', 'mAP': 0.5537994791942625, 'sharpness': 109.57168312479284, 'contrast': 58.85119504820724},
        {'bitrate': '8000', 'mAP': 0.5480135352710278, 'sharpness': 116.7295484743854, 'contrast': 58.72067853855087},
        {'bitrate': '9000', 'mAP': 0.554382296482627, 'sharpness': 111.43780699791562, 'contrast': 58.653252630155635},
        {'bitrate': '10000', 'mAP': 0.5432808054182178, 'sharpness': 144.3458257902683, 'contrast': 59.2204062067859}]
    data_1680_yolov5s = [
        {'bitrate': '500', 'mAP': 0.3472456073512509, 'sharpness': 99.90232177030998, 'contrast': 58.041528424191505},
        {'bitrate': '1000', 'mAP': 0.3997092794017779, 'sharpness': 79.87281104183715, 'contrast': 59.50342120210514},
        {'bitrate': '1500', 'mAP': 0.43245380011192136, 'sharpness': 85.12458261711976, 'contrast': 59.17485795482186},
        {'bitrate': '2000', 'mAP': 0.44853062766066465, 'sharpness': 93.88755238525415, 'contrast': 59.2322245261167},
        {'bitrate': '2500', 'mAP': 0.4591590874947174, 'sharpness': 98.20473351815167, 'contrast': 59.42353048116412},
        {'bitrate': '3000', 'mAP': 0.46178817679640605, 'sharpness': 102.82838159645375, 'contrast': 59.56600243608433},
        {'bitrate': '3500', 'mAP': 0.4675196865651187, 'sharpness': 102.84523359329793, 'contrast': 59.31474844551592},
        {'bitrate': '4000', 'mAP': 0.4696814058628575, 'sharpness': 103.1384289573714, 'contrast': 59.19617041344503},
        {'bitrate': '4500', 'mAP': 0.4705447000773792, 'sharpness': 106.46893313482744, 'contrast': 59.61812952455157},
        {'bitrate': '5000', 'mAP': 0.4726810476982769, 'sharpness': 106.17390516193248, 'contrast': 59.44949518061699},
        {'bitrate': '5500', 'mAP': 0.47692157682898134, 'sharpness': 107.08840240058079,
         'contrast': 59.284397330423744},
        {'bitrate': '6000', 'mAP': 0.4740335434867686, 'sharpness': 106.13736779979097, 'contrast': 59.3136323274593},
        {'bitrate': '7000', 'mAP': 0.47751377072461654, 'sharpness': 109.57168312479284, 'contrast': 58.85119504820724},
        {'bitrate': '8000', 'mAP': 0.47685824461424964, 'sharpness': 116.7295484743854, 'contrast': 58.72067853855087},
        {'bitrate': '9000', 'mAP': 0.48023666176094776, 'sharpness': 111.43780699791562,
         'contrast': 58.653252630155635},
        {'bitrate': '10000', 'mAP': 0.4699538216522115, 'sharpness': 144.3458257902683, 'contrast': 59.2204062067859}]
    data_1440_yolov5s = [
        {'bitrate': '500', 'mAP': 0.31452677548060326, 'sharpness': 135.52794779208833, 'contrast': 58.06480144073285},
        {'bitrate': '1000', 'mAP': 0.3615955363124287, 'sharpness': 100.49844175359732, 'contrast': 59.141833316098186},
        {'bitrate': '1500', 'mAP': 0.3978264026174375, 'sharpness': 112.14855847254942, 'contrast': 59.157058571747385},
        {'bitrate': '2000', 'mAP': 0.41415288992600996, 'sharpness': 118.3274017929406, 'contrast': 59.400183973377125},
        {'bitrate': '2500', 'mAP': 0.4203098611790312, 'sharpness': 125.41949336966954, 'contrast': 59.6330611009344},
        {'bitrate': '3000', 'mAP': 0.42556091682702135, 'sharpness': 129.1206409593695, 'contrast': 59.28164384129008},
        {'bitrate': '3500', 'mAP': 0.43242186409982797, 'sharpness': 130.8821502015623, 'contrast': 59.62523084064519},
        {'bitrate': '4000', 'mAP': 0.43727714654014116, 'sharpness': 132.1237364104464, 'contrast': 59.4066976922451},
        {'bitrate': '4500', 'mAP': 0.4348332962106999, 'sharpness': 134.3672404538698, 'contrast': 59.456174711261916},
        {'bitrate': '5000', 'mAP': 0.44065938611441813, 'sharpness': 136.5919557081383, 'contrast': 59.255232970140085},
        {'bitrate': '5500', 'mAP': 0.44313087697193626, 'sharpness': 137.79004458507254, 'contrast': 59.22985753695238},
        {'bitrate': '6000', 'mAP': 0.4449868607547362, 'sharpness': 137.5972734901991, 'contrast': 59.17163467961137},
        {'bitrate': '7000', 'mAP': 0.4450889747150933, 'sharpness': 140.64507712896938, 'contrast': 58.853105443596675},
        {'bitrate': '8000', 'mAP': 0.4480488829389009, 'sharpness': 143.70454589515109, 'contrast': 58.59084022487831},
        {'bitrate': '9000', 'mAP': 0.4461473736206847, 'sharpness': 149.6184312605277, 'contrast': 58.55496477331347},
        {'bitrate': '10000', 'mAP': 0.44301733455792347, 'sharpness': 165.74697049720652,
         'contrast': 58.99029655926553}]
    data_1440_yolov5x = [
        {'bitrate': '500', 'mAP': 0.3798745578756425, 'sharpness': 135.52794779208833, 'contrast': 58.06480144073285},
        {'bitrate': '1000', 'mAP': 0.44163841935365655, 'sharpness': 100.49844175359732,
         'contrast': 59.141833316098186},
        {'bitrate': '1500', 'mAP': 0.47593188419615035, 'sharpness': 112.14855847254942,
         'contrast': 59.157058571747385},
        {'bitrate': '2000', 'mAP': 0.49865845051254043, 'sharpness': 118.3274017929406, 'contrast': 59.400183973377125},
        {'bitrate': '2500', 'mAP': 0.5090282645499167, 'sharpness': 125.41949336966954, 'contrast': 59.6330611009344},
        {'bitrate': '3000', 'mAP': 0.5137058050943524, 'sharpness': 129.1206409593695, 'contrast': 59.28164384129008},
        {'bitrate': '3500', 'mAP': 0.5238426741994257, 'sharpness': 130.8821502015623, 'contrast': 59.62523084064519},
        {'bitrate': '4000', 'mAP': 0.5264814289730961, 'sharpness': 132.1237364104464, 'contrast': 59.4066976922451},
        {'bitrate': '4500', 'mAP': 0.5272905603199947, 'sharpness': 134.3672404538698, 'contrast': 59.456174711261916},
        {'bitrate': '5000', 'mAP': 0.5275436859391174, 'sharpness': 136.5919557081383, 'contrast': 59.255232970140085},
        {'bitrate': '5500', 'mAP': 0.5341723366282093, 'sharpness': 137.79004458507254, 'contrast': 59.22985753695238},
        {'bitrate': '6000', 'mAP': 0.5360863190929867, 'sharpness': 137.5972734901991, 'contrast': 59.17163467961137},
        {'bitrate': '7000', 'mAP': 0.5354042504845279, 'sharpness': 140.64507712896938, 'contrast': 58.853105443596675},
        {'bitrate': '8000', 'mAP': 0.5336886258840476, 'sharpness': 143.70454589515109, 'contrast': 58.59084022487831},
        {'bitrate': '9000', 'mAP': 0.5302128414024647, 'sharpness': 149.6184312605277, 'contrast': 58.55496477331347},
        {'bitrate': '10000', 'mAP': 0.5277288209810793, 'sharpness': 165.74697049720652, 'contrast': 58.99029655926553}]
    data = data_1440_yolov5x
    data = sorted(data, key=lambda x: int(x['bitrate']))
    bitrate = [int(d['bitrate']) for d in data]
    accuracy = [d['mAP'] for d in data]
    # accuracy = normalized(accuracy)
    sharpness = normalized([d['sharpness'] for d in data])
    contrast = normalized([d['contrast'] for d in data])
    plt.figure(figsize=(9, 6))
    plt.plot(bitrate, accuracy)
    plt.plot(bitrate, sharpness)
    plt.plot(bitrate, contrast)
    plt.legend(['Accuracy', 'Sharpness', 'Contrast'])
    plt.xlabel('Bitrate (Kbps)')
    plt.show()


def handle_frames(bitrate, path, weight, caches):
    baseline = path.endswith('baseline')
    dump_dir = path
    if not baseline:
        dump_dir = os.path.join(path, 'dump')
    if baseline:
        indexes = [p.split('.')[0] for p in os.listdir(dump_dir) if p.endswith(f'{weight}.txt')]
        indexes = [int(i) for i in indexes if i.isnumeric()]
        indexes = sorted(indexes)
    else:
        indexes = sorted([int(p.split('.')[0]) for p in os.listdir(dump_dir) if p.endswith('.bin')])
    if len(os.listdir(dump_dir)) < 20:
        return None
    detections = parse_results_accuracy(path, weight=weight)
    detections = {int(k): v for k, v in detections.items()}
    accuracy = get_results_accuracy(detections, path, weight=weight)
    mAP = accuracy['mAP']
    sharpness = []
    contrast = []
    for index in indexes:
        res = handle_frame0(path, weight, caches, index, baseline=baseline, accuracy=False)
        sharpness.append(res['sharpness'])
        contrast.append(res['contrast'])
    return {'bitrate': bitrate, 'mAP': mAP, 'sharpness': np.median(sharpness), 'contrast': np.median(contrast)}


def main():
    args = parse_args()
    path = args.path
    records = {}
    for d in os.listdir(path):
        d = os.path.join(path, d)
        meta_path = os.path.join(d, 'metadata.txt')
        if not os.path.isfile(meta_path):
            continue
        meta = get_meta(meta_path)
        records.setdefault(meta['resolution'], {})[meta['bitrate']] = d
    resolution = '1440x1280'
    weight = 'yolov5x'
    caches = load_caches()
    # res = handle_frames(0, os.path.expanduser('~/Data/webrtc_exp3/baseline'), weight, caches)
    with Pool(12) as pool:
        res = pool.starmap(handle_frames,
                           [(bitrate, path, weight, caches) for bitrate, path in records[resolution].items()])
    print(res)


if __name__ == '__main__':
    # main()
    illustrate()
