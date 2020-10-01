import matplotlib.pyplot as plt


def main():
    # dlatency pair (avg, med)
    # how to quantify encoding quality
    # get both median and standard deviation
    # 
    data = {'vp8':
                {3500: {'encoding': [62.710144927536234, 62.0], 'decoding': [61.90243902439025, 61.0],
                        'transmission': [24.536585365853657, 23.0], 'overall': [157.9219512195122, 157.0],
                        'accuracy': [0.562605484373256, 0.40627515241015016], 'bandwidth': []},
                 3000: {'encoding': [56.54545454545455, 57.0], 'decoding': [66.24744897959184, 69.0],
                        'encoded_size': [],
                        'transmission': [23.349489795918366, 21.0], 'overall': [155.09183673469389, 156.0],
                        'accuracy': [0.5277201346989752, 0.42328566373721643], 'bandwidth': []},
                 2500: {'encoding': [52.9622641509434, 53.0], 'decoding': [63.5, 68.0],
                        'transmission': [28.246835443037973, 28.0], 'overall': [152.623417721519, 154.0],
                        'accuracy': [0.48233681232436315, 0.4074302970755493], 'bandwidth': []},
                 2000: {'encoding': [53.22883295194508, 54.0], 'decoding': [64.2015503875969, 68.0],
                        'transmission': [], 'overall': [148.54521963824288, 147.0],
                        'accuracy': [0.5106755181437654, 0.3946788031183316], 'bandwidth': []},
                 1500: {'encoding': [], 'decoding': [56.89514066496164, 61.0],
                        'transmission': [24.35021319230804, 21.93333339691162],
                        'overall': [137.85149196468655, 138.93333339691162, ],
                        'accuracy': [0.48207814024238205, 0.381933503354583], 'bandwidth': []},
                 }
            }
    print(data)

    plt.figure(figsize=(10, 5))
    plt.rcParams.update({'font.size': 16})
    plt.xlabel('Bitrate (kbps)')
    plt.ylabel('Average precision')
    plt.title('Bitrate\' impact on average precision (VP8, YOLOv5, weight: yolov5s)')
    x = list(data['vp8'].keys())
    y1 = [float(data['vp8'][k]['accuracy'][0]) for k in x]
    y2 = [float(data['vp8'][k]['accuracy'][1]) for k in x]
    plt.plot(x, y1)
    plt.plot(x, y2)
    # plt.ylim(0, .8)
    plt.legend(['Pedestrian', 'Vehicle'])
    plt.savefig('accuracy_vp8.png', dpi=600)
    plt.show()


if __name__ == '__main__':
    main()
