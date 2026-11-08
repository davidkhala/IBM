import json
import os
import unittest

from dotenv import load_dotenv

from src.config import Settings
from src.wxo import WxoClient, parse_sse_line

load_dotenv()


def sse(event: str, data: dict) -> str:
    """真实 wxo 的格式:每行一个裸 JSON 事件。"""
    return json.dumps({"id": "1-0", "event": event, "data": data}) + "\n\n"


class ParseSseTestCase(unittest.TestCase):
    def test_delta(self):
        line = sse("message.delta", {"thread_id": "t1", "delta": {"content": [{"text": "Hel"}, {"text": "lo"}]}}).strip()
        d = parse_sse_line(line)
        self.assertEqual((d.text, d.thread_id, d.done), ("Hello", "t1", False))

    def test_standard_sse_prefix_is_accepted(self):
        line = "data: " + sse("message.delta", {"delta": {"content": [{"text": "x"}]}}).strip()
        self.assertEqual(parse_sse_line(line).text, "x")

    def test_completed_and_done(self):
        self.assertTrue(parse_sse_line(sse("message.completed", {}).strip()).done)
        self.assertTrue(parse_sse_line("data: [DONE]").done)

    def test_ignored_lines(self):
        for line in ("", "event: x", "data:", ": keepalive"):
            self.assertIsNone(parse_sse_line(line))

    def test_other_event_carries_thread_id(self):
        d = parse_sse_line(sse("run.started", {"thread_id": "t9"}).strip())
        self.assertEqual((d.text, d.thread_id, d.done), ("", "t9", False))


class WxoClientTestCase(unittest.IsolatedAsyncioTestCase):
    """依赖本地运行的 wxo Developer Edition;连接信息取自环境变量或 .env(WXO_*)。"""

    def make(self, **overrides) -> WxoClient:
        env = {k: v for k, v in os.environ.items() if k.startswith("WXO_")}
        env.update(overrides)
        return WxoClient(Settings.from_env(env))

    async def test_login_and_resolve_agent(self):
        client = self.make()
        try:
            self.assertTrue(await client.agent_id())
        finally:
            await client.aclose()

    async def test_stream_and_continue_thread(self):
        client = self.make()
        try:
            first = [d async for d in client.stream("Reply with one short sentence.")]
            self.assertTrue(first[-1].done)
            self.assertTrue("".join(d.text for d in first).strip())
            thread_id = next(d.thread_id for d in first if d.thread_id)

            second = [d async for d in client.stream("Thanks.", thread_id)]
            self.assertTrue(second[-1].done)
            self.assertEqual(next(d.thread_id for d in second if d.thread_id), thread_id)
        finally:
            await client.aclose()

    async def test_relogin_on_expired_token(self):
        client = self.make()
        try:
            await client.login()
            client._token = "expired"
            self.assertTrue(await client.agent_id())
        finally:
            await client.aclose()

    async def test_unknown_agent(self):
        client = self.make(WXO_AGENT="no-such-agent-for-test")
        try:
            with self.assertRaises(RuntimeError):
                await client.agent_id()
        finally:
            await client.aclose()


if __name__ == "__main__":
    unittest.main()
