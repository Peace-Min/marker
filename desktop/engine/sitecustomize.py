"""Offline runtime policy, inherited by every bundled Python subprocess."""
import ipaddress
import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"
os.environ["PYTHONNOUSERSITE"] = "1"


def loopback(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="replace")
    if host in ("localhost", "localhost.localdomain"):
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except (ValueError, AttributeError):
        return False


def offline_only(event, args):
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple) and not loopback(address[0]):
            raise PermissionError(f"OFFLINE_POLICY: external connection refused: {address[0]}")
    elif event == "socket.getaddrinfo" and not loopback(args[0]):
        raise PermissionError(f"OFFLINE_POLICY: external DNS refused: {args[0]}")


sys.addaudithook(offline_only)
