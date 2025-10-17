#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

__version__ = '.'.join(map(lambda i: "%s" % i, (0, 0, 2)))

import sys
import datetime
import asyncio
import socket
import warnings
from collections import deque
from typing import Deque

try:
    from gpiozero import CPUTemperature, LED
except ImportError:  # pragma: no cover - fallback for non-RPi environments
    warnings.warn("gpiozero not installed; using no-op fallbacks")

    class CPUTemperature:  # type: ignore
        def __init__(self):
            self.temperature = 0.0

    class LED:  # type: ignore
        def __init__(self, pin: int):
            self.is_active = False

        def on(self) -> None:
            self.is_active = True

        def off(self) -> None:
            self.is_active = False


HOST = '0.0.0.0'
PORT = 9527


class CPUTemperatureMonitor(object):
    periodic_ttl = 5
    logsize = 60
    t = 0
    t_on = 60
    t_off_offset = 10

    def __init__(self):
        self.data: Deque[str] = deque(maxlen=self.logsize)
        self.fun = LED(14)
        self.t_off = self.t_on - self.t_off_offset
        self._cpu = CPUTemperature()
        self._response_bytes: bytes = b""

    def append(self, x: str) -> None:
        self.data.append(x)

    def get(self):
        return list(self.data)

    def _build_response_bytes(self) -> bytes:
        title = f"FAND | {round(self.t)}&deg;C | {self.fun.is_active}"
        lines = [
            "<html>",
            f"<meta http-equiv=\"refresh\" content=\"{self.periodic_ttl}\"/>",
            f"<title>{title}</title>",
            f"<body><h3>CPU temperature monitor version {__version__}</h3>",
            (
                f"temperature current: {self.t}&deg;C "
                f"on: {self.t_on}&deg;C "
                f"off: {self.t_off}&deg;C "
                f"fun state: {'Off' if self.fun.is_active is False else 'On'}"
            ),
            "<pre>",
        ]

        for item in reversed(self.data):
            if item:
                lines.append(str(item))

        lines += [
            "</pre>",
            "</body>",
            "</html>",
        ]

        body = "\n".join(lines).encode()
        headers = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            + f"Content-Length: {len(body)}\r\n".encode()
            + b"Connection: close\r\n\r\n"
        )
        return headers + body

    async def server(self, loop, host=HOST, port=PORT):
        async def handler(conn):
            try:
                await loop.sock_recv(conn, 1024)
                await loop.sock_sendall(conn, self._response_bytes)
            finally:
                conn.close()

        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.setblocking(False)
        _socket.bind((host, port))
        _socket.listen(10)

        while True:
            conn, _addr = await loop.sock_accept(_socket)
            loop.create_task(handler(conn))

    async def periodic(self):
        while True:
            ts = datetime.datetime.now().isoformat()
            self.t = self._cpu.temperature

            if self.t > self.t_on and self.fun.is_active is False:
                self.fun.on()
            elif self.t < self.t_off and self.fun.is_active is True:
                self.fun.off()

            log_state = 'Off' if self.fun.is_active is False else 'On'
            logstr = f"{ts} {self.t} {log_state}"
            print(logstr)
            self.append(logstr)

            # Refresh cached HTTP response after data change
            self._response_bytes = self._build_response_bytes()

            await asyncio.sleep(self.periodic_ttl)

    @classmethod
    def run(cls):
        monitor = cls()

        async def main():
            loop = asyncio.get_running_loop()
            # Initialize cached response before serving
            monitor._response_bytes = monitor._build_response_bytes()
            server_task = asyncio.create_task(monitor.server(loop))
            periodic_task = asyncio.create_task(monitor.periodic())
            await asyncio.gather(server_task, periodic_task)

        try:
            # Try to enable uvloop if present for better performance
            try:
                import uvloop  # type: ignore
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            except Exception:
                pass

            asyncio.run(main())
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    CPUTemperatureMonitor.run()


