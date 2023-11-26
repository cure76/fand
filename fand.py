#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

__version__ = '.'.join(map(lambda i: "%s" % i, (0, 0, 1)))

import sys
import copy
import datetime
import asyncio
import socket
import warnings

from http.server import BaseHTTPRequestHandler
from io import BytesIO

try:
    from gpiozero import CPUTemperature, LED

except ImportError:
    warnings.warn("Warning: gpiozero not installed")


HOST = '0.0.0.0'
PORT = 9527


class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = BytesIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message


class CPUTemperatureMonitor(object):
    periodic_ttl = 5
    logsize = 60
    t = 0
    t_on = 60
    t_off_offset = 10

    def __init__(self):
        self.data = [None for i in range(self.logsize)]
        self.fun = LED(14)
        self.t_off = self.t_on - self.t_off_offset

    def append(self, x):
        self.data.pop(0)
        self.data.append(x)

    def get(self):
        return self.data

    async def server(self, loop, host=HOST, port=PORT):

        def response():
            resp = "HTTP/1.1 200 OK\r\n"
            resp += "Content-Type: text/html\r\n"
            resp += "\r\n"
            resp += "<html>"
            resp += "<meta http-equiv=\"refresh\" content=\"{0}\"/>".format(self.periodic_ttl)
            resp += "<title>FAND | {0}&deg;C | {1}</title>".format(round(self.t), self.fun.is_active)
            resp += "<body><h3>CPU temperature monitor version {0}</h3></body>".format(__version__)
            resp += "temperature current: {0}&deg;C on: {1}&deg;C off: {2}&deg;C fun state: {3}".format(
                self.t, self.t_on, self.t_off, 'Off' if self.fun.is_active is False else 'On'
            )
            resp += "<pre>"
            _data = copy.copy(self.get())
            _data.reverse()
            for item in _data:
                if item:
                    resp += str(item) + '\n'
            resp += "</pre>"
            resp += "</html>"
            return resp

        async def handler(conn):
            req = await loop.sock_recv(conn, 1024)

            if req:
                resp = response().encode()
                await loop.sock_sendall(conn, resp)
            conn.close()

        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.setblocking(False)
        _socket.bind((host, port))
        _socket.listen(10)

        while True:
            conn, addr = await loop.sock_accept(_socket)
            loop.create_task(handler(conn))

    @asyncio.coroutine
    def periodic(self):
        while True:
            ts = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
            self.t = CPUTemperature().temperature

            if self.t > self.t_on and self.fun.is_active is False:
                self.fun.on()

            if self.t < self.t_off and self.fun.is_active is True:
                self.fun.off()

            logstr = '{0} {1} {2}'.format(ts, self.t, 'Off' if self.fun.is_active is False else 'On')
            print(logstr)
            self.append(logstr)
            yield from asyncio.sleep(self.periodic_ttl)

    @classmethod
    def run(cls):
        monitor = cls()

        task = asyncio.Task(monitor.periodic())
        loop = asyncio.get_event_loop()

        try:
            loop.run_until_complete(monitor.server(loop))
            loop.run_until_complete(task)
            loop.run_forever()

        except (asyncio.CancelledError, KeyboardInterrupt):
            pass

        finally:
            task.cancel()
            loop.call_later(0, task.cancel)
            loop.close()


if __name__ == '__main__':
    CPUTemperatureMonitor.run()


