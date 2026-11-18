"""Device broker: descriptor passing and waiting for a re-enumerating scanner."""
import errno
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import pika_broker  # noqa: E402


class BrokerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.node = self.root/'video4'; self.node.write_bytes(b'camera')
        self.calls = 0

    def discover(self):
        # The scanner is absent for the first two looks, as while it reboots.
        self.calls += 1
        if self.calls <= 2:
            return []
        return [{'serial': 'SER1', 'nodes': {'0:0': str(self.node)}}]

    def start(self, serial='SER1'):
        sock = self.root/'b.sock'
        log = open(os.devnull, 'w'); self.addCleanup(log.close)
        t = threading.Thread(target=pika_broker.serve, daemon=True, kwargs=dict(
            path=sock, serial=serial, log=log, discover=self.discover, wait=2,
            opener=lambda n: os.open(n, os.O_RDONLY | os.O_CLOEXEC)))
        t.start()
        for _ in range(100):
            if sock.exists(): break
            threading.Event().wait(.02)
        return sock

    def test_passes_descriptor_after_scanner_returns(self):
        sock = self.start()
        fd = pika_broker.request_fd(sock, '0:0')
        try:
            self.assertEqual(os.read(fd, 6), b'camera')
        finally:
            os.close(fd)
        self.assertGreaterEqual(self.calls, 3)

    def test_refuses_unknown_endpoint_and_other_scanner(self):
        sock = self.start()
        with self.assertRaises(OSError) as e:
            pika_broker.request_fd(sock, '../etc/passwd')
        self.assertEqual(e.exception.errno, errno.EINVAL)
        with self.assertRaises(OSError) as e:
            pika_broker.request_fd(sock, '2:1')   # this scanner has no such endpoint
        self.assertEqual(e.exception.errno, errno.ENODEV)

    def test_wrong_serial_gets_nothing(self):
        sock = self.start(serial='OTHER')
        with self.assertRaises(OSError) as e:
            pika_broker.request_fd(sock, '0:0')
        self.assertEqual(e.exception.errno, errno.ENODEV)


if __name__ == '__main__':
    unittest.main()
