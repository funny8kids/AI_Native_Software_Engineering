#!/usr/bin/env python3
"""极简 Chrome DevTools Protocol 客户端（仅 Python 标准库 + 本机 google-chrome）。

为什么要手写：本机没有 playwright / selenium / websocket-client，而交互类判据
（命中测试、真实点击、控制台错误）必须驱动真浏览器。Chrome 的 CLI 只提供
--dump-dom 与 --screenshot，二者都只能看静态结果，看不见"谁压在谁上面"——
本轮"整页不可点击"的致命缺陷正是靠 DOM 读数漏掉、靠 elementFromPoint 抓到的。

用法：
    with Chrome(width=1280, height=900) as page:
        page.navigate("http://127.0.0.1:8080/#/guide")
        page.wait_for("document.querySelector('.markdown-section')")
        print(page.js("location.hash"))
        page.click(640, 400)
"""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
import shutil

CHROME = os.environ.get("AINSE_CHROME", "/usr/bin/google-chrome")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class WebSocket:
    """够用的 WebSocket 客户端：文本帧、客户端掩码、分片重组、ping/pong。"""

    def __init__(self, url: str, timeout: float = 60.0):
        scheme, rest = url.split("://", 1)
        assert scheme in ("ws", "wss"), scheme
        hostport, _, path = rest.partition("/")
        path = "/" + path
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=timeout)
        self.buf = b""
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket 握手被断开")
            head += chunk
        status, _, self.buf = head.partition(b"\r\n\r\n")
        if b" 101 " not in status.split(b"\r\n")[0] + b" ":
            raise RuntimeError("WebSocket 握手失败: %r" % status.split(b"\r\n")[0])

    def _exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("WebSocket 连接被对端关闭")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _frame(self, opcode: int, payload: bytes) -> None:
        header = bytearray([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        self.sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def send_text(self, text: str) -> None:
        self._frame(0x1, text.encode())

    def close(self) -> None:
        try:
            self._frame(0x8, b"")
        except OSError:
            pass
        self.sock.close()

    def recv_text(self) -> str:
        """取一条完整的文本消息（跳过控制帧、重组分片）。"""
        parts = []
        while True:
            b0, b1 = self._exact(2)
            fin, opcode = b0 & 0x80, b0 & 0x0F
            masked, n = b1 & 0x80, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._exact(8))[0]
            mask = self._exact(4) if masked else None
            payload = self._exact(n) if n else b""
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise RuntimeError("WebSocket 被对端关闭")
            if opcode == 0x9:
                self._frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x0:
                parts.append(payload)
            else:
                parts = [payload]
            if fin:
                return b"".join(parts).decode("utf-8", "replace")


class CDP:
    """一个浏览器进程 + 一个页面 target，同步调用，事件按名收集。"""

    def __init__(self, width: int = 1280, height: int = 900):
        self.width, self.height = width, height
        self.proc = None
        self.profile = None
        self.ws = None
        self.session = None
        self._next_id = 0
        self.events: list[dict] = []

    # ---------- 生命周期 ----------
    def start(self) -> "CDP":
        self.port = free_port()
        self.profile = tempfile.mkdtemp(prefix="ainse-cdp-")
        self.proc = subprocess.Popen(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                f"--remote-debugging-port={self.port}",
                f"--user-data-dir={self.profile}",
                f"--window-size={self.width},{self.height}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 45
        version = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/version", timeout=2) as r:
                    version = json.load(r)
                break
            except Exception:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"Chrome 启动失败（退出码 {self.proc.returncode}），可执行文件：{CHROME}")
                time.sleep(0.3)
        if version is None:
            raise RuntimeError("等待 Chrome DevTools 端点超时")
        self.ws = WebSocket(version["webSocketDebuggerUrl"])
        self.session = self.call("Target.createTarget", {"url": "about:blank"})["targetId"]
        self.session = self.call("Target.attachToTarget", {"targetId": self.session, "flatten": True})["sessionId"]
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Log.enable")
        self.set_viewport(self.width, self.height)
        return self

    def stop(self) -> None:
        for closer in (lambda: self.ws and self.ws.close(), lambda: self.proc and self.proc.terminate()):
            try:
                closer()
            except Exception:
                pass
        if self.proc:
            try:
                self.proc.wait(timeout=8)
            except Exception:
                self.proc.kill()
        if self.profile:
            shutil.rmtree(self.profile, ignore_errors=True)

    def __enter__(self) -> "CDP":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # ---------- 协议 ----------
    def call(self, method: str, params: dict | None = None, timeout: float = 60.0):
        self._next_id += 1
        mid = self._next_id
        msg = {"id": mid, "method": method, "params": params or {}}
        if self.session and not method.startswith("Target."):
            msg["sessionId"] = self.session
        self.ws.send_text(json.dumps(msg))
        deadline = time.time() + timeout
        while time.time() < deadline:
            data = json.loads(self.ws.recv_text())
            if data.get("id") == mid:
                if "error" in data:
                    raise RuntimeError(f"{method} 失败：{data['error']}")
                return data.get("result", {})
            if "method" in data:
                self.events.append(data)
        raise TimeoutError(f"{method} 超时")

    def drain_events(self, names) -> list[dict]:
        got = [e for e in self.events if e.get("method") in names]
        self.events = [e for e in self.events if e.get("method") not in names]
        return got

    # ---------- 页面 ----------
    def set_viewport(self, width: int, height: int, mobile: bool = False) -> None:
        self.width, self.height = width, height
        self.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": mobile},
        )

    def navigate(self, url: str, timeout: float = 60.0) -> None:
        self.call("Page.navigate", {"url": url}, timeout=timeout)

    def reload(self, timeout: float = 60.0) -> None:
        self.call("Page.reload", {"ignoreCache": True}, timeout=timeout)

    def js(self, expression: str, await_promise: bool = False, timeout: float = 60.0):
        r = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": await_promise,
                "timeout": int(timeout * 1000),
            },
            timeout=timeout + 10,
        )
        if r.get("exceptionDetails"):
            raise RuntimeError("页面内异常：%s" % json.dumps(r["exceptionDetails"], ensure_ascii=False)[:400])
        return r.get("result", {}).get("value")

    def wait_for(self, predicate_js: str, timeout: float = 25.0, interval: float = 0.15) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.js("!!(%s)" % predicate_js):
                return True
            time.sleep(interval)
        return False

    def click(self, x: int, y: int) -> None:
        """真·鼠标点击（CDP Input 域），与用户按下发生在命中测试同一坐标。"""
        base = {"x": int(x), "y": int(y), "button": "left", "buttons": 1, "clickCount": 1}
        self.call("Input.dispatchMouseEvent", dict(base, type="mouseMoved"))
        self.call("Input.dispatchMouseEvent", dict(base, type="mousePressed"))
        self.call("Input.dispatchMouseEvent", dict(base, type="mouseReleased", buttons=0))

    def screenshot(self, path: str) -> None:
        data = self.call("Page.captureScreenshot", {"format": "png"})["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
