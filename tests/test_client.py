from pathlib import Path

import pytest

from fastdfs_client.client import Config, FastdfsClient, get_tracker_conf, is_ip_v4
from fastdfs_client.exceptions import ConfigError


def test_ip():
    assert is_ip_v4("8.8.8.8")
    assert not is_ip_v4("8.8.8.1234")
    assert not is_ip_v4("8.8.8.a")
    assert not is_ip_v4("8.8.8")
    assert not is_ip_v4("8.8.8")


def test_config_create():
    ip = "192.168.0.2"
    assert Config.create((ip,)) == {
        "host_tuple": (ip,),
        "port": Config.port,
        "timeout": Config.timeout,
        "name": Config.name,
    }


def test_conf_file():
    parent = Path(__file__).parent
    assert (
        get_tracker_conf("tests/trackers.conf")
        == FastdfsClient(parent / "trackers.conf").trackers
        == {
            "host_tuple": ("192.168.0.2",),
            "name": "Tracker Pool",
            "port": 22122,
            "timeout": 30,
        }
    )
    with pytest.raises(ConfigError):
        FastdfsClient(parent / "invalid.conf")


def test_conf_string():
    assert (
        FastdfsClient(("192.168.0.2",)).trackers
        == FastdfsClient(["192.168.0.2"]).trackers
        == {
            "host_tuple": ("192.168.0.2",),
            "name": "Tracker Pool",
            "port": 22122,
            "timeout": 30,
        }
    )


def test_upload_url():
    to_upload = Path(__file__)
    domain = "dfs.waketzheng.top"
    client = FastdfsClient([domain])
    url = client.upload_as_url(to_upload.read_bytes(), to_upload.suffix)
    assert Path(url).suffix == to_upload.suffix
    assert domain in url
    assert url.startswith("https")
    remote_file_id = url.split("://")[-1].split("/", 1)[-1]
    r = client.delete_file(remote_file_id)
    assert "success" in str(r)


def test_upload_filename():
    domain = "dfs.waketzheng.top"
    client = FastdfsClient([domain])
    ret = client.upload_by_filename(__file__)
    assert ret["Group name"].startswith("group")
    remote_file_id = ret["Remote file_id"]
    assert ret["Local file name"] in __file__
    r = client.delete_file(remote_file_id)
    assert remote_file_id in str(r)
