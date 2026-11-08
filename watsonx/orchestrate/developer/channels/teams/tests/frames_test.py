import json
import unittest
import uuid

from src import frames


class FramesTestCase(unittest.TestCase):
    def test_header_roundtrip(self):
        id_ = uuid.uuid4()
        header = frames.encode_header(frames.REQUEST, 123, id_, True)
        self.assertEqual(len(header), frames.HEADER_LENGTH)
        self.assertEqual(frames.decode_header(header), (frames.REQUEST, 123, id_, True))

    def test_header_wire_format(self):
        id_ = uuid.UUID("12345678-1234-5678-1234-567812345678")
        self.assertEqual(
            frames.encode_header(frames.STREAM, 5, id_, False),
            b"S.000005.12345678-1234-5678-1234-567812345678.0\n",
        )

    def test_malformed_header(self):
        with self.assertRaises(ValueError):
            frames.decode_header(b"x" * 48)
        with self.assertRaises(ValueError):
            frames.decode_header(b"short")

    def test_parser_handles_split_and_merged_bytes(self):
        id_ = uuid.uuid4()
        payload = json.dumps({"verb": "POST", "path": "/api/messages"}).encode()
        wire = b"".join(h + c for h, c in frames.encode_payload(frames.REQUEST, id_, payload))
        parser = frames.FrameParser()
        out = []
        for i in range(0, len(wire), 7):  # 任意切分
            out += parser.feed(wire[i:i + 7])
        self.assertEqual([(f.type, f.id, f.payload) for f in out], [(frames.REQUEST, id_, payload)])

    def test_large_payload_is_chunked_and_reassembled(self):
        id_ = uuid.uuid4()
        payload = b"a" * (frames.CHUNK_SIZE * 2 + 10)
        chunks = frames.encode_payload(frames.STREAM, id_, payload)
        self.assertEqual(len(chunks), 3)
        parser = frames.FrameParser()
        out = parser.feed(b"".join(h + c for h, c in chunks))
        self.assertEqual(out[0].payload, payload)

    def test_empty_payload(self):
        id_ = uuid.uuid4()
        out = frames.FrameParser().feed(b"".join(h + c for h, c in frames.encode_payload(frames.STREAM, id_, b"")))
        self.assertEqual(out[0].payload, b"")

    def test_cancel_stream_discards_partial(self):
        id_ = uuid.uuid4()
        parser = frames.FrameParser()
        parser.feed(frames.encode_header(frames.STREAM, 3, id_, False) + b"abc")
        parser.feed(frames.encode_header(frames.CANCEL_STREAM, 0, id_, True))
        out = parser.feed(frames.encode_header(frames.STREAM, 2, id_, True) + b"de")
        self.assertEqual(out[0].payload, b"de")


if __name__ == "__main__":
    unittest.main()
