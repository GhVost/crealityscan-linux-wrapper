"""Host-side Pika device broker.

The sandbox only sees the scanner's device nodes that existed at launch. When the
scanner re-enumerates (it reboots into calibration mode, and after firmware
updates), the kernel creates new nodes the sandbox can't see. This broker runs
outside the sandbox, finds the same scanner again by serial number, opens the
requested camera node and hands the open file descriptor to the helper inside the
sandbox over a Unix socket (SCM_RIGHTS). Only the scanner's four camera endpoints
of the scanner with the expected serial are ever opened; nothing else in /dev is
reachable through it.

Protocol (one request per connection): the client sends an endpoint key
("0:0", "0:1", "2:0" or "2:1": USB interface:video index) and a newline. The
broker replies "OK\\n" with the descriptor attached, or "ERR <errno>\\n".
"""
import errno
import os
from pathlib import Path
import socket
import sys
import time

KEYS = ('0:0', '0:1', '2:0', '2:1')
WAIT_SECONDS = 3  # below the bridge's 4 s reply limit; the SDK retries while the scanner reboots


def default_discover():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools/pika-recorder'))
    from device import discover
    return discover()


def find_node(serial, key, discover=default_discover, wait=WAIT_SECONDS, sleep=time.sleep):
    """Device node for `key` of the Pika with `serial`, waiting while it reboots."""
    deadline = time.monotonic() + wait
    while True:
        try:
            for d in discover():
                if d['serial'] == serial and key in d['nodes']:
                    return d['nodes'][key]
        except (OSError, RuntimeError):
            pass  # sysfs entries come and go while the device re-enumerates
        if time.monotonic() >= deadline:
            raise OSError(errno.ENODEV, 'Pika not present')
        sleep(0.25)


def serve(path, serial, log=sys.stdout, discover=default_discover, opener=None, wait=WAIT_SECONDS):
    opener = opener or (lambda node: os.open(node, os.O_RDWR | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW))
    path = Path(path)
    if path.exists() or path.is_symlink():
        path.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM | socket.SOCK_CLOEXEC)
    old = os.umask(0o177)
    try:
        server.bind(str(path))
    finally:
        os.umask(old)
    server.listen(8)
    print('READY Pika device broker', flush=True, file=log)
    try:
        while True:
            conn, _ = server.accept()
            with conn:
                conn.settimeout(WAIT_SECONDS + 5)
                request = '?'
                try:
                    request = conn.recv(16).split(b'\n', 1)[0].decode('ascii', 'replace')
                    if request not in KEYS:
                        raise OSError(errno.EINVAL, 'unknown endpoint')
                    node = find_node(serial, request, discover, wait)
                    fd = opener(node)
                    try:
                        socket.send_fds(conn, [b'OK\n'], [fd])
                    finally:
                        os.close(fd)
                    print(f'OPENED {request} {node}', flush=True, file=log)
                except OSError as e:
                    code = e.errno or errno.EIO
                    print(f'REFUSED {request}: {e}', flush=True, file=log)
                    try:
                        conn.sendall(f'ERR {code}\n'.encode())
                    except OSError:
                        pass
    finally:
        server.close()
        try:
            path.unlink()
        except OSError:
            pass


def request_fd(path, key, timeout=WAIT_SECONDS + 5):
    """Client side, for the helpers: an open descriptor for `key`."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM | socket.SOCK_CLOEXEC) as s:
        s.settimeout(timeout)
        s.connect(str(path))
        s.sendall(key.encode() + b'\n')
        msg, fds, _, _ = socket.recv_fds(s, 64, 1)
        if msg.startswith(b'OK') and fds:
            return fds[0]
        for fd in fds:
            os.close(fd)
        code = int(msg.split()[1]) if msg.startswith(b'ERR') and len(msg.split()) > 1 else errno.EIO
        raise OSError(code, os.strerror(code))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: pika_broker.py SOCKET SERIAL')
    try:
        serve(sys.argv[1], sys.argv[2])
    except KeyboardInterrupt:
        pass
