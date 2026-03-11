from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any, Optional


class QMPError(RuntimeError):
    pass

@dataclass
class QMPClient:
    host: str
    port: int
    timeout: float = 5.0
    _sock: Optional[socket.socket] = None
    _buf: bytes = b""

    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        # greeting
        _ = self._read_msg()
        self.execute("qmp_capabilities")

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def _read_line(self) -> bytes:
        assert self._sock is not None
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise QMPError("QMP socket closed")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return line

    def _read_msg(self) -> dict[str, Any]:
        line = self._read_line()
        try:
            return json.loads(line.decode("utf-8"))
        except Exception as e:
            raise QMPError(f"Failed to parse QMP JSON: {line!r}") from e

    def execute(self, cmd: str, arguments: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        assert self._sock is not None
        msg: dict[str, Any] = {"execute": cmd}
        if arguments:
            msg["arguments"] = arguments
        data = (json.dumps(msg) + "\n").encode("utf-8")
        self._sock.sendall(data)

        # Consume responses until we see {"return": ...} or {"error": ...}
        while True:
            resp = self._read_msg()
            if "return" in resp:
                return resp["return"]
            if "error" in resp:
                raise QMPError(str(resp["error"]))
            # Ignore async events here; callers can be extended to handle them.
