DEFAULT_HTTP_CONTROL_PORT = 8090
DEFAULT_TCP_CONTROL_PORT = 8081
DEFAULT_UDP_CONTROL_PORT = 8082
DEFAULT_UDP_DATA_SINK_PORT = 8083
DEFAULT_UDP_DATA_POUR_PORT = 8084
DEFAULT_TCP_DATA_SINK_PORT = 8085
DEFAULT_TCP_DATA_POUR_PORT = 8086
DEFAULT_UDP_PROBING_PORT = 8087
DEFAULT_UDP_PORT = 8088
DEFAULT_DATA_RATE = 30 * 1024 * 1024  # Client's/Server's sending data rate in bps
DEFAULT_PACKET_SIZE = 1 * 1024
DEFAULT_RUNNING_PERIOD = 3600

IP_HEADER_SIZE = 20
UDP_HEADER_SIZE = 8
ID_LENGTH = 36
SEQ_LENGTH = 4
CONTENT_LENGTH = 10
TIMESTAMP_BYTES = 8
ACK_PREFIX_LENGTH = 3
ACK_BUF = "ACK".encode()
PKG_LENGTH = SEQ_LENGTH + CONTENT_LENGTH
PKG_IP_LENGTH = PKG_LENGTH + IP_HEADER_SIZE + UDP_HEADER_SIZE
ACK_LENGTH = SEQ_LENGTH + ACK_PREFIX_LENGTH + TIMESTAMP_BYTES
PACKET_SEQUENCE_BYTES = 4
PACKET_SEQUENCE_BITS = 8 * PACKET_SEQUENCE_BYTES
BYTE_ORDER = 'big'
MTU = 1464

SINR_ARRAY_BUFFER_SIZE = 5

# Dataflow:
# Client -> Server: request, indication the type of communication
# Server -> Client: ACK
# Start network flows
