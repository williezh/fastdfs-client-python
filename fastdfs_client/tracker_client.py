import os
import struct
from dataclasses import dataclass
from datetime import datetime

import anyio

from .connection import tcp_receive, tcp_recv_response, tcp_send_data
from .exceptions import ConnectionError, DataError, ResponseError
from .protols import (
    FDFS_GROUP_NAME_MAX_LEN,
    FDFS_SPACE_SIZE_BASE_INDEX,
    FDFS_STORAGE_STATUS_ACTIVE,
    FDFS_STORAGE_STATUS_DELETED,
    FDFS_STORAGE_STATUS_INIT,
    FDFS_STORAGE_STATUS_IP_CHANGED,
    FDFS_STORAGE_STATUS_OFFLINE,
    FDFS_STORAGE_STATUS_ONLINE,
    FDFS_STORAGE_STATUS_RECOVERY,
    FDFS_STORAGE_STATUS_SYNCING,
    FDFS_STORAGE_STATUS_WAIT_SYNC,
    IP_ADDRESS_SIZE,
    TRACKER_PROTO_CMD_SERVER_LIST_ALL_GROUPS,
    TRACKER_PROTO_CMD_SERVER_LIST_ONE_GROUP,
    TRACKER_PROTO_CMD_SERVER_LIST_STORAGE,
    TRACKER_PROTO_CMD_SERVICE_QUERY_FETCH_ONE,
    TRACKER_PROTO_CMD_SERVICE_QUERY_STORE_WITH_GROUP_ONE,
    TRACKER_PROTO_CMD_SERVICE_QUERY_STORE_WITHOUT_GROUP_ONE,
    TRACKER_PROTO_CMD_SERVICE_QUERY_UPDATE,
    TRACKER_QUERY_STORAGE_FETCH_BODY_LEN,
    TRACKER_QUERY_STORAGE_STORE_BODY_LEN,
    StorageServer,
    TrackerHeader,
)
from .utils import appromix


def parse_storage_status(status_code):
    try:
        ret = {
            FDFS_STORAGE_STATUS_INIT: "INIT",
            FDFS_STORAGE_STATUS_WAIT_SYNC: "WAIT_SYNC",
            FDFS_STORAGE_STATUS_SYNCING: "SYNCING",
            FDFS_STORAGE_STATUS_IP_CHANGED: "IP_CHANGED",
            FDFS_STORAGE_STATUS_DELETED: "DELETED",
            FDFS_STORAGE_STATUS_OFFLINE: "OFFLINE",
            FDFS_STORAGE_STATUS_ONLINE: "ONLINE",
            FDFS_STORAGE_STATUS_ACTIVE: "ACTIVE",
            FDFS_STORAGE_STATUS_RECOVERY: "RECOVERY",
        }[status_code]
    except KeyError:
        ret = "UNKNOW"
    return ret


@dataclass
class StorageInfo:
    status = 0
    id = ""
    ip_addr = ""
    domain_name = ""
    src_id = ""
    version = ""
    join_time = datetime.fromtimestamp(0).isoformat()
    up_time = datetime.fromtimestamp(0).isoformat()
    totalMB = ""
    freeMB = ""
    upload_prio = 0
    store_path_count = 0
    subdir_count_per_path = 0
    curr_write_path = 0
    storage_port = 23000
    storage_http_port = 80
    alloc_count = 0
    current_count = 0
    max_count = 0
    total_upload_count = 0
    success_upload_count = 0
    total_append_count = 0
    success_append_count = 0
    total_modify_count = 0
    success_modify_count = 0
    total_truncate_count = 0
    success_truncate_count = 0
    total_setmeta_count = 0
    success_setmeta_count = 0
    total_del_count = 0
    success_del_count = 0
    total_download_count = 0
    success_download_count = 0
    total_getmeta_count = 0
    success_getmeta_count = 0
    total_create_link_count = 0
    success_create_link_count = 0
    total_del_link_count = 0
    success_del_link_count = 0
    total_upload_bytes = 0
    success_upload_bytes = 0
    total_append_bytes = 0
    success_append_bytes = 0
    total_modify_bytes = 0
    success_modify_bytes = 0
    total_download_bytes = 0
    success_download_bytes = 0
    total_sync_in_bytes = 0
    success_sync_in_bytes = 0
    total_sync_out_bytes = 0
    success_sync_out_bytes = 0
    total_file_open_count = 0
    success_file_open_count = 0
    total_file_read_count = 0
    success_file_read_count = 0
    total_file_write_count = 0
    success_file_write_count = 0
    last_source_sync = datetime.fromtimestamp(0).isoformat()
    last_sync_update = datetime.fromtimestamp(0).isoformat()
    last_synced_time = datetime.fromtimestamp(0).isoformat()
    last_heartbeat_time = datetime.fromtimestamp(0).isoformat()
    if_trunk_server = ""
    # fmt = |-status(1)-ipaddr(16)-domain(128)-srcipaddr(16)-ver(6)-52*8-|
    fmt = "!B 16s 16s 128s 16s 6s 10Q 4s4s4s 42Q?"

    def set_info(self, bytes_stream):
        (
            self.status,
            self.id,
            ip_addr,
            domain_name,
            self.src_id,
            version,
            join_time,
            up_time,
            totalMB,
            freeMB,
            self.upload_prio,
            self.store_path_count,
            self.subdir_count_per_path,
            self.curr_write_path,
            self.storage_port,
            self.storage_http_port,
            self.alloc_count,
            self.current_count,
            self.max_count,
            self.total_upload_count,
            self.success_upload_count,
            self.total_append_count,
            self.success_append_count,
            self.total_modify_count,
            self.success_modify_count,
            self.total_truncate_count,
            self.success_truncate_count,
            self.total_setmeta_count,
            self.success_setmeta_count,
            self.total_del_count,
            self.success_del_count,
            self.total_download_count,
            self.success_download_count,
            self.total_getmeta_count,
            self.success_getmeta_count,
            self.total_create_link_count,
            self.success_create_link_count,
            self.total_del_link_count,
            self.success_del_link_count,
            self.total_upload_bytes,
            self.success_upload_bytes,
            self.total_append_bytes,
            self.total_append_bytes,
            self.total_modify_bytes,
            self.success_modify_bytes,
            self.total_download_bytes,
            self.success_download_bytes,
            self.total_sync_in_bytes,
            self.success_sync_in_bytes,
            self.total_sync_out_bytes,
            self.success_sync_out_bytes,
            self.total_file_open_count,
            self.success_file_open_count,
            self.total_file_read_count,
            self.success_file_read_count,
            self.total_file_write_count,
            self.success_file_write_count,
            last_source_sync,
            last_sync_update,
            last_synced_time,
            last_heartbeat_time,
            self.if_trunk_server,
        ) = struct.unpack(self.fmt, bytes_stream)
        try:
            self.ip_addr = ip_addr.strip(b"\x00")
            self.domain_name = domain_name.strip(b"\x00")
            self.version = version.strip(b"\x00")
            self.totalMB = appromix(totalMB, FDFS_SPACE_SIZE_BASE_INDEX)
            self.freeMB = appromix(freeMB, FDFS_SPACE_SIZE_BASE_INDEX)
        except ValueError:
            msg = "[-] Error: disk space overrun, can not represented it."
            raise ResponseError(msg) from None
        self.join_time = datetime.fromtimestamp(join_time).isoformat()
        self.up_time = datetime.fromtimestamp(up_time).isoformat()
        self.last_source_sync = datetime.fromtimestamp(last_source_sync).isoformat()
        self.last_sync_update = datetime.fromtimestamp(last_sync_update).isoformat()
        self.last_synced_time = datetime.fromtimestamp(last_synced_time).isoformat()
        self.last_heartbeat_time = datetime.fromtimestamp(
            last_heartbeat_time
        ).isoformat()
        return True

    def __str__(self):
        """Transform to readable string."""

        s = "Storage information:\n"
        s += "\tip_addr = %s (%s)\n" % (self.ip_addr, parse_storage_status(self.status))
        s += "\thttp domain = %s\n" % self.domain_name
        s += "\tversion = %s\n" % self.version
        s += "\tjoin time = %s\n" % self.join_time
        s += "\tup time = %s\n" % self.up_time
        s += "\ttotal storage = %s\n" % self.totalMB
        s += "\tfree storage = %s\n" % self.freeMB
        s += "\tupload priority = %d\n" % self.upload_prio
        s += "\tstore path count = %d\n" % self.store_path_count
        s += "\tsubdir count per path = %d\n" % self.subdir_count_per_path
        s += "\tstorage port = %d\n" % self.storage_port
        s += "\tstorage HTTP port = %d\n" % self.storage_http_port
        s += "\tcurrent write path = %d\n" % self.curr_write_path
        s += "\tsource ip_addr = %s\n" % self.ip_addr
        s += f"\tif_trunk_server = {self.if_trunk_server}\n"
        s += "\ttotal upload count = %ld\n" % self.total_upload_count
        s += "\tsuccess upload count = %ld\n" % self.success_upload_count
        s += "\ttotal download count = %ld\n" % self.total_download_count
        s += "\tsuccess download count = %ld\n" % self.success_download_count
        s += "\ttotal append count = %ld\n" % self.total_append_count
        s += "\tsuccess append count = %ld\n" % self.success_append_count
        s += "\ttotal modify count = %ld\n" % self.total_modify_count
        s += "\tsuccess modify count = %ld\n" % self.success_modify_count
        s += "\ttotal truncate count = %ld\n" % self.total_truncate_count
        s += "\tsuccess truncate count = %ld\n" % self.success_truncate_count
        s += "\ttotal delete count = %ld\n" % self.total_del_count
        s += "\tsuccess delete count = %ld\n" % self.success_del_count
        s += "\ttotal set_meta count = %ld\n" % self.total_setmeta_count
        s += "\tsuccess set_meta count = %ld\n" % self.success_setmeta_count
        s += "\ttotal get_meta count = %ld\n" % self.total_getmeta_count
        s += "\tsuccess get_meta count = %ld\n" % self.success_getmeta_count
        s += "\ttotal create link count = %ld\n" % self.total_create_link_count
        s += "\tsuccess create link count = %ld\n" % self.success_create_link_count
        s += "\ttotal delete link count = %ld\n" % self.total_del_link_count
        s += "\tsuccess delete link count = %ld\n" % self.success_del_link_count
        s += "\ttotal upload bytes = %ld\n" % self.total_upload_bytes
        s += "\tsuccess upload bytes = %ld\n" % self.success_upload_bytes
        s += "\ttotal download bytes = %ld\n" % self.total_download_bytes
        s += "\tsuccess download bytes = %ld\n" % self.success_download_bytes
        s += "\ttotal append bytes = %ld\n" % self.total_append_bytes
        s += "\tsuccess append bytes = %ld\n" % self.success_append_bytes
        s += "\ttotal modify bytes = %ld\n" % self.total_modify_bytes
        s += "\tsuccess modify bytes = %ld\n" % self.success_modify_bytes
        s += "\ttotal sync_in bytes = %ld\n" % self.total_sync_in_bytes
        s += "\tsuccess sync_in bytes = %ld\n" % self.success_sync_in_bytes
        s += "\ttotal sync_out bytes = %ld\n" % self.total_sync_out_bytes
        s += "\tsuccess sync_out bytes = %ld\n" % self.success_sync_out_bytes
        s += "\ttotal file open count = %ld\n" % self.total_file_open_count
        s += "\tsuccess file open count = %ld\n" % self.success_file_open_count
        s += "\ttotal file read count = %ld\n" % self.total_file_read_count
        s += "\tsuccess file read count = %ld\n" % self.success_file_read_count
        s += "\ttotal file write count = %ld\n" % self.total_file_write_count
        s += "\tsucess file write count = %ld\n" % self.success_file_write_count
        s += "\tlast heartbeat time = %s\n" % self.last_heartbeat_time
        s += "\tlast source update = %s\n" % self.last_source_sync
        s += "\tlast sync update = %s\n" % self.last_sync_update
        s += "\tlast synced time = %s\n" % self.last_synced_time
        return s

    def get_fmt_size(self):
        return struct.calcsize(self.fmt)


@dataclass
class GroupInfo:
    group_name = ""
    totalMB = ""
    freeMB = ""
    trunk_freeMB = ""
    count = 0
    storage_port = 0
    store_http_port = 0
    active_count = 0
    curr_write_server = 0
    store_path_count = 0
    subdir_count_per_path = 0
    curr_trunk_file_id = 0
    fmt = "!%ds 11Q" % (FDFS_GROUP_NAME_MAX_LEN + 1)

    def __str__(self):
        s = "Group information:\n"
        s += "\tgroup name = %s\n" % self.group_name
        s += "\ttotal disk space = %s\n" % self.totalMB
        s += "\tdisk free space = %s\n" % self.freeMB
        s += "\ttrunk free space = %s\n" % self.trunk_freeMB
        s += "\tstorage server count = %d\n" % self.count
        s += "\tstorage port = %d\n" % self.storage_port
        s += "\tstorage HTTP port = %d\n" % self.store_http_port
        s += "\tactive server count = %d\n" % self.active_count
        s += "\tcurrent write server index = %d\n" % self.curr_write_server
        s += "\tstore path count = %d\n" % self.store_path_count
        s += "\tsubdir count per path = %d\n" % self.subdir_count_per_path
        s += "\tcurrent trunk file id = %d\n" % self.curr_trunk_file_id
        return s

    def set_info(self, bytes_stream):
        (
            group_name,
            totalMB,
            freeMB,
            trunk_freeMB,
            self.count,
            self.storage_port,
            self.store_http_port,
            self.active_count,
            self.curr_write_server,
            self.store_path_count,
            self.subdir_count_per_path,
            self.curr_trunk_file_id,
        ) = struct.unpack(self.fmt, bytes_stream)
        try:
            self.group_name = group_name.strip(b"\x00")
            self.freeMB = appromix(freeMB, FDFS_SPACE_SIZE_BASE_INDEX)
            self.totalMB = appromix(totalMB, FDFS_SPACE_SIZE_BASE_INDEX)
            self.trunk_freeMB = appromix(trunk_freeMB, FDFS_SPACE_SIZE_BASE_INDEX)
        except ValueError:
            msg = "[-] Error disk space overrun, can not represented it."
            raise DataError(msg) from None

    def get_fmt_size(self):
        return struct.calcsize(self.fmt)


class TrackerClient:
    """Class Tracker client."""

    def __init__(self, pool):
        self.pool = pool

    def tracker_list_servers(self, group_name, storage_ip=None):
        """
        List servers in a storage group
        """
        conn = self.pool.get_connection()
        th = TrackerHeader()
        ip_len = len(storage_ip) if storage_ip else 0
        if ip_len >= IP_ADDRESS_SIZE:
            ip_len = IP_ADDRESS_SIZE - 1
        th.pkg_len = FDFS_GROUP_NAME_MAX_LEN + ip_len
        th.cmd = TRACKER_PROTO_CMD_SERVER_LIST_STORAGE
        group_fmt = "!%ds" % FDFS_GROUP_NAME_MAX_LEN
        store_ip_addr = storage_ip or ""
        storage_ip_fmt = "!%ds" % ip_len
        try:
            th.send_header(conn)
            send_buffer = struct.pack(group_fmt, group_name) + struct.pack(
                storage_ip_fmt, store_ip_addr
            )
            tcp_send_data(conn, send_buffer)
            th.recv_header(conn)
            if th.status != 0:
                raise DataError(
                    "[-] Error: %d, %s" % (th.status, os.strerror(th.status))
                )
            recv_buffer, recv_size = tcp_recv_response(conn, th.pkg_len)
            si = StorageInfo()
            si_fmt_size = si.get_fmt_size()
            recv_size = len(recv_buffer)
            if recv_size % si_fmt_size != 0:
                errinfo = (
                    "[-] Error: response size not match, expect: %d, actual: %d"
                    % (th.pkg_len, recv_size)
                )
                raise ResponseError(errinfo)
        except ConnectionError:
            raise
        finally:
            self.pool.release(conn)
        num_storage = recv_size / si_fmt_size
        si_list = []
        i = 0
        while num_storage:
            si.set_info(recv_buffer[(i * si_fmt_size) : ((i + 1) * si_fmt_size)])
            si_list.append(si)
            si = StorageInfo()
            num_storage -= 1
            i += 1
        ret_dict = {}
        ret_dict["Group name"] = group_name
        ret_dict["Servers"] = si_list
        return ret_dict

    def tracker_list_one_group(self, group_name):
        conn = self.pool.get_connection()
        th = TrackerHeader()
        th.pkg_len = FDFS_GROUP_NAME_MAX_LEN
        th.cmd = TRACKER_PROTO_CMD_SERVER_LIST_ONE_GROUP
        # group_fmt: |-group_name(16)-|
        group_fmt = "!%ds" % FDFS_GROUP_NAME_MAX_LEN
        try:
            th.send_header(conn)
            send_buffer = struct.pack(group_fmt, group_name)
            tcp_send_data(conn, send_buffer)
            th.recv_header(conn)
            if th.status != 0:
                raise DataError(
                    "[-] Error: %d, %s" % (th.status, os.strerror(th.status))
                )
            recv_buffer, recv_size = tcp_recv_response(conn, th.pkg_len)
            group_info = GroupInfo()
            group_info.set_info(recv_buffer)
        except ConnectionError:
            raise
        finally:
            self.pool.release(conn)
        return group_info

    def tracker_list_all_groups(self):
        conn = self.pool.get_connection()
        th = TrackerHeader()
        th.cmd = TRACKER_PROTO_CMD_SERVER_LIST_ALL_GROUPS
        try:
            th.send_header(conn)
            th.recv_header(conn)
            if th.status != 0:
                raise DataError(
                    "[-] Error: %d, %s" % (th.status, os.strerror(th.status))
                )
            recv_buffer, recv_size = tcp_recv_response(conn, th.pkg_len)
        except:
            raise
        finally:
            self.pool.release(conn)
        gi = GroupInfo()
        gi_fmt_size = gi.get_fmt_size()
        if recv_size % gi_fmt_size != 0:
            errmsg = "[-] Error: Response size is mismatch, except: %d, actul: %d" % (
                th.pkg_len,
                recv_size,
            )
            raise ResponseError(errmsg)
        num_groups = recv_size / gi_fmt_size
        ret_dict = {}
        ret_dict["Groups count"] = num_groups
        gi_list = []
        i = 0
        while num_groups:
            gi.set_info(recv_buffer[i * gi_fmt_size : (i + 1) * gi_fmt_size])
            gi_list.append(gi)
            gi = GroupInfo()
            i += 1
            num_groups -= 1
        ret_dict["Groups"] = gi_list
        return ret_dict

    def tracker_query_storage_stor_without_group(self):
        """Query storage server for upload, without group name.
        Return: StorageServer object"""
        th = TrackerHeader(cmd=TRACKER_PROTO_CMD_SERVICE_QUERY_STORE_WITHOUT_GROUP_ONE)
        with self.pool.open_connection() as conn:
            th.send_header(conn)
            th.recv_header(conn)
            if th.status != 0:
                raise DataError(
                    "[-] Error: %d, %s" % (th.status, os.strerror(th.status))
                )
            recv_buffer, recv_size = tcp_recv_response(conn, th.pkg_len)
            if recv_size != TRACKER_QUERY_STORAGE_STORE_BODY_LEN:
                errmsg = "[-] Error: Tracker response length is invaild, "
                errmsg += "expect: %d, actual: %d" % (
                    TRACKER_QUERY_STORAGE_STORE_BODY_LEN,
                    recv_size,
                )
                raise ResponseError(errmsg)
        # recv_fmt |-group_name(16)-ipaddr(16-1)-port(8)-store_path_index(1)|
        recv_fmt = "!%ds %ds Q B" % (FDFS_GROUP_NAME_MAX_LEN, IP_ADDRESS_SIZE - 1)
        store_serv = StorageServer()
        (group_name, ip_addr, store_serv.port, store_serv.store_path_index) = (
            struct.unpack(recv_fmt, recv_buffer)
        )
        store_serv.group_name = group_name.strip(b"\x00")
        store_serv.ip_addr = ip_addr.strip(b"\x00")
        return store_serv

    def tracker_query_storage_stor_with_group(self, group_name):
        """Query storage server for upload, based group name.
        arguments:
        @group_name: string
        @Return StorageServer object
        """
        conn = self.pool.get_connection()
        th = TrackerHeader()
        th.cmd = TRACKER_PROTO_CMD_SERVICE_QUERY_STORE_WITH_GROUP_ONE
        th.pkg_len = FDFS_GROUP_NAME_MAX_LEN
        th.send_header(conn)
        group_fmt = "!%ds" % FDFS_GROUP_NAME_MAX_LEN
        send_buffer = struct.pack(group_fmt, group_name)
        try:
            tcp_send_data(conn, send_buffer)
            th.recv_header(conn)
            if th.status != 0:
                raise DataError("Error: %d, %s" % (th.status, os.strerror(th.status)))
            recv_buffer, recv_size = tcp_recv_response(conn, th.pkg_len)
            if recv_size != TRACKER_QUERY_STORAGE_STORE_BODY_LEN:
                errmsg = "[-] Error: Tracker response length is invaild, "
                errmsg += "expect: %d, actual: %d" % (
                    TRACKER_QUERY_STORAGE_STORE_BODY_LEN,
                    recv_size,
                )
                raise ResponseError(errmsg)
        except ConnectionError:
            raise
        finally:
            self.pool.release(conn)
        # recv_fmt: |-group_name(16)-ipaddr(16-1)-port(8)-store_path_index(1)-|
        recv_fmt = "!%ds %ds Q B" % (FDFS_GROUP_NAME_MAX_LEN, IP_ADDRESS_SIZE - 1)
        store_serv = StorageServer()
        (group, ip_addr, store_serv.port, store_serv.store_path_index) = struct.unpack(
            recv_fmt, recv_buffer
        )
        store_serv.group_name = group.strip(b"\x00")
        store_serv.ip_addr = ip_addr.strip(b"\x00")
        return store_serv

    def _tracker_do_query_storage(self, group_name, filename, cmd):
        """
        core of query storage, based group name and filename.
        It is useful download, delete and set meta.
        arguments:
        @group_name: string
        @filename: string. remote file_id
        @Return: StorageServer object
        """
        conn = self.pool.get_connection()
        th = TrackerHeader()
        file_name_len = len(filename)
        th.pkg_len = FDFS_GROUP_NAME_MAX_LEN + file_name_len
        th.cmd = cmd
        th.send_header(conn)
        # query_fmt: |-group_name(16)-filename(file_name_len)-|
        query_fmt = "!%ds %ds" % (FDFS_GROUP_NAME_MAX_LEN, file_name_len)
        send_buffer = struct.pack(query_fmt, group_name.encode(), filename.encode())
        try:
            tcp_send_data(conn, send_buffer)
            th.recv_header(conn)
            if th.status != 0:
                raise DataError("Error: %d, %s" % (th.status, os.strerror(th.status)))
            recv_buffer, recv_size = tcp_recv_response(conn, th.pkg_len)
            if recv_size != TRACKER_QUERY_STORAGE_FETCH_BODY_LEN:
                errmsg = "[-] Error: Tracker response length is invaild, "
                errmsg += "expect: %d, actual: %d" % (th.pkg_len, recv_size)
                raise ResponseError(errmsg)
        except ConnectionError:
            raise
        finally:
            self.pool.release(conn)
        # recv_fmt: |-group_name(16)-ip_addr(16)-port(8)-|
        recv_fmt = "!%ds %ds Q" % (FDFS_GROUP_NAME_MAX_LEN, IP_ADDRESS_SIZE - 1)
        store_serv = StorageServer()
        (group_name, ipaddr, store_serv.port) = struct.unpack(recv_fmt, recv_buffer)
        store_serv.group_name = group_name.strip(b"\x00")
        store_serv.ip_addr = ipaddr.strip(b"\x00")
        return store_serv

    def tracker_query_storage_update(self, group_name, filename):
        """
        Query storage server to update(delete and set_meta).
        """
        return self._tracker_do_query_storage(
            group_name, filename, TRACKER_PROTO_CMD_SERVICE_QUERY_UPDATE
        )

    def tracker_query_storage_fetch(self, group_name, filename):
        """
        Query storage server to download.
        """
        return self._tracker_do_query_storage(
            group_name, filename, TRACKER_PROTO_CMD_SERVICE_QUERY_FETCH_ONE
        )

    @staticmethod
    async def get_storage_server(
        host_info: tuple[str, int], group_name="", filename=""
    ) -> StorageServer:
        """Query storage server for upload, without group name.
        Return: StorageServer object"""
        pkg_len = file_name_len = len(filename)
        if is_delete := bool(file_name_len):
            cmd = TRACKER_PROTO_CMD_SERVICE_QUERY_UPDATE
            pkg_len += FDFS_GROUP_NAME_MAX_LEN
        else:
            cmd = TRACKER_PROTO_CMD_SERVICE_QUERY_STORE_WITHOUT_GROUP_ONE
        th = TrackerHeader(cmd=cmd, pkg_len=pkg_len)
        async with await anyio.connect_tcp(*host_info) as client:
            await client.send(th.build_header())
            expected_len = TRACKER_QUERY_STORAGE_STORE_BODY_LEN
            if is_delete:
                expected_len = TRACKER_QUERY_STORAGE_FETCH_BODY_LEN
                # query_fmt: |-group_name(16)-filename(file_name_len)-|
                query_fmt = "!%ds %ds" % (FDFS_GROUP_NAME_MAX_LEN, file_name_len)
                send_buffer = struct.pack(
                    query_fmt, group_name.encode(), filename.encode()
                )
                await client.send(send_buffer)
            await th.verify_header(client)
            recv_buffer = await tcp_receive(client, th.pkg_len, expected_len)
        if is_delete:
            # recv_fmt: |-group_name(16)-ip_addr(16)-port(8)-|
            recv_fmt = "!%ds %ds Q" % (FDFS_GROUP_NAME_MAX_LEN, IP_ADDRESS_SIZE - 1)
            group, ip, port = struct.unpack(recv_fmt, recv_buffer)
            path_index = 0
        else:
            # recv_fmt |-group_name(16)-ipaddr(16-1)-port(8)-store_path_index(1)|
            recv_fmt = "!%ds %ds Q B" % (FDFS_GROUP_NAME_MAX_LEN, IP_ADDRESS_SIZE - 1)
            group, ip, port, path_index = struct.unpack(recv_fmt, recv_buffer)
        return StorageServer(
            group_name=group.strip(b"\x00"),
            ip_addr=ip.strip(b"\x00"),
            port=port,
            store_path_index=path_index,
        )
