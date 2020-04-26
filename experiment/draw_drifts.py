import matplotlib.pyplot as plt

def main():
    data = []
    with open('data/drifts.txt') as f:
        for line in f.readlines():
            line = line.strip()
            if line:
                try:
                    line = int(line)
                    data.append(line)
                except Exception as e:
                    pass
    print(sum(data) / len(data))
    #plt.plot(data)
    #plt.show()


if __name__ == '__main__':
    main()

