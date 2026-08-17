import socket
import threading
import time


class FreenoveClient:
    """Single TCP client for the Freenove server's CRLF-delimited protocol."""

    def __init__(self, host, port=5000, on_line=None, on_state=None):
        self.host = host
        self.port = int(port)
        self.on_line = on_line or (lambda line: None)
        self.on_state = on_state or (lambda connected, error=None: None)
        self.sock = None
        self.connected = False
        self._stop = threading.Event()
        self._send_lock = threading.Lock()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._close()

    def send(self, command):
        if not self.connected or self.sock is None:
            raise ConnectionError("Freenove server is not connected")
        wire = command.strip().encode("utf-8") + b"\r\n"
        with self._send_lock:
            self.sock.sendall(wire)

    def _close(self):
        self.connected = False
        sock, self.sock = self.sock, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def _run(self):
        delay = 1
        while not self._stop.is_set():
            try:
                sock = socket.create_connection((self.host, self.port), timeout=3)
                sock.settimeout(2)
                self.sock = sock
                self.connected = True
                self.on_state(True, None)
                delay = 1
                # Enable server queue-count feedback.
                self.send("S12 K1")
                buffer = b""
                while not self._stop.is_set():
                    try:
                        chunk = sock.recv(4096)
                    except socket.timeout:
                        continue
                    if not chunk:
                        raise ConnectionError("Freenove server closed the connection")
                    buffer += chunk
                    while b"\r\n" in buffer:
                        raw, buffer = buffer.split(b"\r\n", 1)
                        line = raw.decode("utf-8", errors="replace").strip()
                        if line:
                            self.on_line(line)
            except Exception as exc:
                self._close()
                self.on_state(False, str(exc))
                if not self._stop.wait(delay):
                    delay = min(delay * 2, 15)


def format_move(x, y, z):
    return f"G0 X{x:g} Y{y:g} Z{z:g}"


def format_servo(index, angle):
    return f"S9 I{index:d} A{angle:d}"

