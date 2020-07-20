import getpass

## Network topology
#
#   UE <------> gNB <-------------> UPF <----------> MEC
#  lab7                             upf              lab4
#
#
HOSTS = {
    "MEC": {
        "Name": "lab4",
        "IP": "195.148.127.233",
        "IP_private": "10.22.1.51",
        "User": "lix16",
    },
    "UPF": {
        "Name": "upf",
        "IP": "10.22.1.50",
        "User": "ubuntu",
    },
    "UE": {
        "Name": "lab7",
        "IP": "127.0.0.1",  # If script is running in the UE
        "User": "lix16",
    },
    "DEV": {
        "Name": "lab6",
        "IP": "195.148.127.108",
        "User": "lix16",
    },
    "LOCAL": {
        "Name": "localhost",
        "IP": "localhost",
        "User": getpass.getuser(),
    }
}
