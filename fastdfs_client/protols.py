import os
import socket
import struct
from contextlib import asynccontextmanager
from dataclasses import dataclass

import anyio

from .exceptions import ConnectionError, DataError

# define FDFS protol constans
TRACKER_PROTO_CMD_STORAGE_JOIN = 81
FDFS_PROTO_CMD_QUIT = 82
TRACKER_PROTO_CMD_STORAGE_BEAT = 83  # storage heart beat
TRACKER_PROTO_CMD_STORAGE_REPORT_DISK_USAGE = 84  # report disk usage
TRACKER_PROTO_CMD_STORAGE_REPLICA_CHG = 85  # repl new storage servers
TRACKER_PROTO_CMD_STORAGE_SYNC_SRC_REQ = 86  # src storage require sync
TRACKER_PROTO_CMD_STORAGE_SYNC_DEST_REQ = 87  # dest storage require sync
TRACKER_PROTO_CMD_STORAGE_SYNC_NOTIFY = 88  # sync done notify
TRACKER_PROTO_CMD_STORAGE_SYNC_REPORT = 89  # report src last synced time as dest server
# dest storage query sync src storage server
TRACKER_PROTO_CMD_STORAGE_SYNC_DEST_QUERY = 79
# storage server report it's ip changed
TRACKER_PROTO_CMD_STORAGE_REPORT_IP_CHANGED = 78
# storage server request storage server's changelog
TRACKER_PROTO_CMD_STORAGE_CHANGELOG_REQ = 77
TRACKER_PROTO_CMD_STORAGE_REPORT_STATUS = 76  # report specified storage server status
TRACKER_PROTO_CMD_STORAGE_PARAMETER_REQ = 75  # storage server request parameters
TRACKER_PROTO_CMD_STORAGE_REPORT_TRUNK_FREE = 74  # storage report trunk free space
TRACKER_PROTO_CMD_STORAGE_REPORT_TRUNK_FID = 73  # storage report current trunk file id
TRACKER_PROTO_CMD_STORAGE_FETCH_TRUNK_FID = 72  # storage get current trunk file id

# start of tracker get system data files
TRACKER_PROTO_CMD_TRACKER_GET_SYS_FILES_START = 61
TRACKER_PROTO_CMD_TRACKER_GET_SYS_FILES_END = 62  # end of tracker get system data files
TRACKER_PROTO_CMD_TRACKER_GET_ONE_SYS_FILE = 63  # tracker get a system data file
TRACKER_PROTO_CMD_TRACKER_GET_STATUS = 64  # tracker get status of other tracker
TRACKER_PROTO_CMD_TRACKER_PING_LEADER = 65  # tracker ping leader
# notify next leader to other trackers
TRACKER_PROTO_CMD_TRACKER_NOTIFY_NEXT_LEADER = 66
# commit next leader to other trackers
TRACKER_PROTO_CMD_TRACKER_COMMIT_NEXT_LEADER = 67

TRACKER_PROTO_CMD_SERVER_LIST_ONE_GROUP = 90
TRACKER_PROTO_CMD_SERVER_LIST_ALL_GROUPS = 91
TRACKER_PROTO_CMD_SERVER_LIST_STORAGE = 92
TRACKER_PROTO_CMD_SERVER_DELETE_STORAGE = 93
TRACKER_PROTO_CMD_SERVICE_QUERY_STORE_WITHOUT_GROUP_ONE = 101
TRACKER_PROTO_CMD_SERVICE_QUERY_FETCH_ONE = 102
TRACKER_PROTO_CMD_SERVICE_QUERY_UPDATE = 103
TRACKER_PROTO_CMD_SERVICE_QUERY_STORE_WITH_GROUP_ONE = 104
TRACKER_PROTO_CMD_SERVICE_QUERY_FETCH_ALL = 105
TRACKER_PROTO_CMD_SERVICE_QUERY_STORE_WITHOUT_GROUP_ALL = 106
TRACKER_PROTO_CMD_SERVICE_QUERY_STORE_WITH_GROUP_ALL = 107
TRACKER_PROTO_CMD_RESP = 100
# active test, tracker and storage both support since V1.28
FDFS_PROTO_CMD_ACTIVE_TEST = 111

STORAGE_PROTO_CMD_REPORT_CLIENT_IP = 9  # ip as tracker client
STORAGE_PROTO_CMD_UPLOAD_FILE = 11
STORAGE_PROTO_CMD_DELETE_FILE = 12
STORAGE_PROTO_CMD_SET_METADATA = 13
STORAGE_PROTO_CMD_DOWNLOAD_FILE = 14
STORAGE_PROTO_CMD_GET_METADATA = 15
STORAGE_PROTO_CMD_SYNC_CREATE_FILE = 16
STORAGE_PROTO_CMD_SYNC_DELETE_FILE = 17
STORAGE_PROTO_CMD_SYNC_UPDATE_FILE = 18
STORAGE_PROTO_CMD_SYNC_CREATE_LINK = 19
STORAGE_PROTO_CMD_CREATE_LINK = 20
STORAGE_PROTO_CMD_UPLOAD_SLAVE_FILE = 21
STORAGE_PROTO_CMD_QUERY_FILE_INFO = 22
STORAGE_PROTO_CMD_UPLOAD_APPENDER_FILE = 23  # create appender file
STORAGE_PROTO_CMD_APPEND_FILE = 24  # append file
STORAGE_PROTO_CMD_SYNC_APPEND_FILE = 25
STORAGE_PROTO_CMD_FETCH_ONE_PATH_BINLOG = 26  # fetch binlog of one store path
STORAGE_PROTO_CMD_RESP = TRACKER_PROTO_CMD_RESP
STORAGE_PROTO_CMD_UPLOAD_MASTER_FILE = STORAGE_PROTO_CMD_UPLOAD_FILE

STORAGE_PROTO_CMD_TRUNK_ALLOC_SPACE = 27  # since V3.00
STORAGE_PROTO_CMD_TRUNK_ALLOC_CONFIRM = 28  # since V3.00
STORAGE_PROTO_CMD_TRUNK_FREE_SPACE = 29  # since V3.00
STORAGE_PROTO_CMD_TRUNK_SYNC_BINLOG = 30  # since V3.00
STORAGE_PROTO_CMD_TRUNK_GET_BINLOG_SIZE = 31  # since V3.07
STORAGE_PROTO_CMD_TRUNK_DELETE_BINLOG_MARKS = 32  # since V3.07
STORAGE_PROTO_CMD_TRUNK_TRUNCATE_BINLOG_FILE = 33  # since V3.07

STORAGE_PROTO_CMD_MODIFY_FILE = 34  # since V3.08
STORAGE_PROTO_CMD_SYNC_MODIFY_FILE = 35  # since V3.08
STORAGE_PROTO_CMD_TRUNCATE_FILE = 36  # since V3.08
STORAGE_PROTO_CMD_SYNC_TRUNCATE_FILE = 37  # since V3.08

# for overwrite all old metadata
STORAGE_SET_METADATA_FLAG_OVERWRITE = "O"
STORAGE_SET_METADATA_FLAG_OVERWRITE_STR = "O"
# for replace, insert when the meta item not exist, otherwise update it
STORAGE_SET_METADATA_FLAG_MERGE = "M"
STORAGE_SET_METADATA_FLAG_MERGE_STR = "M"

FDFS_RECORD_SEPERATOR = "\x01"
FDFS_FIELD_SEPERATOR = "\x02"

# common constants
FDFS_GROUP_NAME_MAX_LEN = 16
IP_ADDRESS_SIZE = 46
FDFS_PROTO_PKG_LEN_SIZE = 8
FDFS_PROTO_CMD_SIZE = 1
FDFS_PROTO_STATUS_SIZE = 1
FDFS_PROTO_IP_PORT_SIZE = IP_ADDRESS_SIZE + 6
FDFS_MAX_SERVERS_EACH_GROUP = 32
FDFS_MAX_GROUPS = 512
FDFS_MAX_TRACKERS = 16
FDFS_DOMAIN_NAME_MAX_LEN = 128

FDFS_MAX_META_NAME_LEN = 64
FDFS_MAX_META_VALUE_LEN = 256

FDFS_FILE_PREFIX_MAX_LEN = 16
FDFS_LOGIC_FILE_PATH_LEN = 10
FDFS_TRUE_FILE_PATH_LEN = 6
FDFS_FILENAME_BASE64_LENGTH = 27
FDFS_TRUNK_FILE_INFO_LEN = 16
FDFS_FILE_EXT_NAME_MAX_LEN = 6
FDFS_SPACE_SIZE_BASE_INDEX = 2  # storage space size based (MB)

FDFS_UPLOAD_BY_BUFFER = 1
FDFS_UPLOAD_BY_FILENAME = 2
FDFS_UPLOAD_BY_FILE = 3
FDFS_DOWNLOAD_TO_BUFFER = 1
FDFS_DOWNLOAD_TO_FILE = 2

FDFS_NORMAL_LOGIC_FILENAME_LENGTH = (
    FDFS_LOGIC_FILE_PATH_LEN
    + FDFS_FILENAME_BASE64_LENGTH
    + FDFS_FILE_EXT_NAME_MAX_LEN
    + 1
)

FDFS_TRUNK_FILENAME_LENGTH = (
    FDFS_TRUE_FILE_PATH_LEN
    + FDFS_FILENAME_BASE64_LENGTH
    + FDFS_TRUNK_FILE_INFO_LEN
    + 1
    + FDFS_FILE_EXT_NAME_MAX_LEN
)
FDFS_TRUNK_LOGIC_FILENAME_LENGTH = FDFS_TRUNK_FILENAME_LENGTH + (
    FDFS_LOGIC_FILE_PATH_LEN - FDFS_TRUE_FILE_PATH_LEN
)

FDFS_VERSION_SIZE = 6

TRACKER_QUERY_STORAGE_FETCH_BODY_LEN = (
    FDFS_GROUP_NAME_MAX_LEN + IP_ADDRESS_SIZE - 1 + FDFS_PROTO_PKG_LEN_SIZE
)
TRACKER_QUERY_STORAGE_STORE_BODY_LEN = (
    FDFS_GROUP_NAME_MAX_LEN + IP_ADDRESS_SIZE - 1 + FDFS_PROTO_PKG_LEN_SIZE + 1
)
# status code, order is important!
FDFS_STORAGE_STATUS_INIT = 0
FDFS_STORAGE_STATUS_WAIT_SYNC = 1
FDFS_STORAGE_STATUS_SYNCING = 2
FDFS_STORAGE_STATUS_IP_CHANGED = 3
FDFS_STORAGE_STATUS_DELETED = 4
FDFS_STORAGE_STATUS_OFFLINE = 5
FDFS_STORAGE_STATUS_ONLINE = 6
FDFS_STORAGE_STATUS_ACTIVE = 7
FDFS_STORAGE_STATUS_RECOVERY = 9
FDFS_STORAGE_STATUS_NONE = 99


@dataclass
class StorageServer:
    """Class storage server for upload."""

    ip_addr: str = ""
    port: int = 0
    group_name: str = ""
    store_path_index: int = 0

    @asynccontextmanager
    async def connect_tcp(self):
        if isinstance(ip_addr := self.ip_addr, bytes):
            ip_addr = ip_addr.decode()
        async with await anyio.connect_tcp(ip_addr, self.port) as client:
            yield client


class Struct(struct.Struct):
    def __repr__(self) -> str:
        return f"struct.Struct({self.format!r})"


@dataclass
class TrackerHeader:
    """
    Class for Pack or Unpack tracker header
        struct tracker_header{
            char pkg_len[FDFS_PROTO_PKG_LEN_SIZE],
            char cmd,
            char status,
        }
    """

    fmt: str = "!QBB"  # pkg_len[FDFS_PROTO_PKG_LEN_SIZE] + cmd + status
    st: Struct = Struct(fmt)
    pkg_len: int = 0
    cmd: int = 0
    status: int = 0

    def _pack(self, pkg_len=0, cmd=0, status=0):
        return self.st.pack(pkg_len, cmd, status)

    def _unpack(self, bytes_stream) -> bool:
        self.pkg_len, self.cmd, self.status = self.st.unpack(bytes_stream)
        return True

    def header_len(self) -> int:
        return self.st.size

    def build_header(self) -> bytes:
        return self._pack(self.pkg_len, self.cmd, self.status)

    def send_header(self, conn) -> None:
        """Send Tracker header to server."""
        header = self.build_header()
        try:
            conn._sock.sendall(header)
        except (socket.error, socket.timeout) as e:
            msg = "[-] Error: while writting to socket: %s" % (e.args,)
            raise ConnectionError(msg) from e

    def recv_header(self, conn) -> None:
        """Receive response from server.
        if sucess, class member (pkg_len, cmd, status) is response.
        """
        try:
            header = conn._sock.recv(self.header_len())
        except (socket.error, socket.timeout) as e:
            msg = "[-] Error: while reading from socket: %s" % (e.args,)
            raise ConnectionError(msg) from e
        self._unpack(header)

    async def verify_header(self, client) -> None:
        response = await client.receive(self.header_len())
        self._unpack(response)
        if (status := self.status) != 0:
            raise DataError(f"[-] Error: {status}, {os.strerror(status)}")


def fdfs_pack_metadata(meta_dict) -> str:
    ret = ""
    for key in meta_dict:
        ret += "%s%c%s%c" % (
            key,
            FDFS_FIELD_SEPERATOR,
            meta_dict[key],
            FDFS_RECORD_SEPERATOR,
        )
    return ret[0:-1]


def fdfs_unpack_metadata(bytes_stream) -> dict:
    li = bytes_stream.split(FDFS_RECORD_SEPERATOR)
    return dict([item.split(FDFS_FIELD_SEPERATOR) for item in li])
