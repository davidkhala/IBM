"""Bot Framework Streaming Extensions 的帧编解码。

帧 = 48 字节头 + 负载。头格式(ASCII):  ``{type}.{length:06d}.{uuid}.{end}\\n``
    type: A=Request, B=Response, S=Stream, X=CancelAll, C=CancelStream
    end : 1 表示该 id 的负载到此结束
"""
import json
import uuid
from dataclasses import dataclass

HEADER_LENGTH = 48
MAX_PAYLOAD = 999_999
CHUNK_SIZE = 64_000
MAX_ASSEMBLED = 16 * 1024 * 1024

REQUEST = "A"
RESPONSE = "B"
STREAM = "S"
CANCEL_ALL = "X"
CANCEL_STREAM = "C"
_TYPES = {REQUEST, RESPONSE, STREAM, CANCEL_ALL, CANCEL_STREAM}


@dataclass(frozen=True)
class Frame:
    """一个已完整组装的负载(同一 type+id 的所有分片已合并)。"""
    type: str
    id: uuid.UUID
    payload: bytes


def encode_header(type_: str, length: int, id_: uuid.UUID, end: bool) -> bytes:
    if type_ not in _TYPES:
        raise ValueError(f"unknown frame type: {type_!r}")
    if not 0 <= length <= MAX_PAYLOAD:
        raise ValueError(f"payload length out of range: {length}")
    return f"{type_}.{length:06d}.{id_}.{int(end)}\n".encode("ascii")


def decode_header(data: bytes) -> tuple[str, int, uuid.UUID, bool]:
    if len(data) != HEADER_LENGTH:
        raise ValueError("malformed header: wrong length")
    try:
        text = data.decode("ascii")
        type_, length, id_, end = text[0], text[2:8], text[9:45], text[46]
        if text[1] != "." or text[8] != "." or text[45] != "." or text[47] != "\n":
            raise ValueError("malformed header: bad delimiter")
        if type_ not in _TYPES or end not in "01" or not length.isdigit():
            raise ValueError("malformed header: bad field")
        return type_, int(length), uuid.UUID(id_), end == "1"
    except UnicodeDecodeError as e:
        raise ValueError("malformed header: not ascii") from e


def encode_payload(type_: str, id_: uuid.UUID, payload: bytes) -> list[tuple[bytes, bytes]]:
    """把一个负载切成若干 (header, chunk);最后一片 end=1。"""
    if not payload:
        return [(encode_header(type_, 0, id_, True), b"")]
    chunks = [payload[i:i + CHUNK_SIZE] for i in range(0, len(payload), CHUNK_SIZE)]
    return [(encode_header(type_, len(c), id_, i == len(chunks) - 1), c) for i, c in enumerate(chunks)]


def json_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class FrameParser:
    """把字节流解析为 Frame。按字节流处理,不依赖 WebSocket 消息边界(头与负载可分可合)。"""

    def __init__(self):
        self._buf = bytearray()
        self._partial: dict[tuple[str, uuid.UUID], bytearray] = {}

    def feed(self, data: bytes) -> list[Frame]:
        self._buf += data
        frames: list[Frame] = []
        while len(self._buf) >= HEADER_LENGTH:
            type_, length, id_, end = decode_header(bytes(self._buf[:HEADER_LENGTH]))
            if len(self._buf) < HEADER_LENGTH + length:
                break
            payload = bytes(self._buf[HEADER_LENGTH:HEADER_LENGTH + length])
            del self._buf[:HEADER_LENGTH + length]

            if type_ in (CANCEL_ALL, CANCEL_STREAM):
                self._partial.pop((STREAM, id_), None)
                continue
            key = (type_, id_)
            part = self._partial.setdefault(key, bytearray())
            part += payload
            if len(part) > MAX_ASSEMBLED:
                raise ValueError("assembled payload too large")
            if end:
                frames.append(Frame(type_, id_, bytes(part)))
                del self._partial[key]
        return frames
