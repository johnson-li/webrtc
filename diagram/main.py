import matplotlib.pyplot as plt


def main():
    # dlatency pair (avg, med)
    data = {'vp8':
                {3000: {'encoding': [24.398337510665527, 24.95703125], 'decoding': [43.901023890784984, 44.0],
                        'transmission': [16.071672354948806, 15.0], 'overall': [115.95221843003414, 118.0],
                        'accuracy': [], 'bandwidth': []},
                 2500: {'encoding': [24.422049506013746, 26.533203125], 'decoding': [62.07560137457045, 59.0],
                        'transmission': [28.57044673539519, 27.0], 'overall': [147.09278350515464, 148.0],
                        'accuracy': [], 'bandwidth': []},
                 2000: {'encoding': [18.38488308097079, 18.58203125], 'decoding': [35.57044673539519, 33.0],
                        'transmission': [15.508591065292096, 15.0], 'overall': [105.60137457044674, 103.0],
                        'accuracy': [], 'bandwidth': []},
                 1500: {'encoding': [18.38488308097079, 18.58203125], 'decoding': [35.57044673539519, 33.0],
                        'transmission': [15.508591065292096, 15.0], 'overall': [105.60137457044674, 103.0],
                        'accuracy': [], 'bandwidth': []},
                 1000: {'encoding': [12.332731175341298, 12.3544921875], 'decoding': [30.320819112627987, 26.0],
                        'transmission': [], 'overall': [],
                        'accuracy': [], 'bandwidth': []},
                 }
            }
    print(data)


if __name__ == '__main__':
    main()
