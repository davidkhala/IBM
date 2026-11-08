from collections import OrderedDict
from collections.abc import AsyncIterator

from .wxo import WxoClient


class Bridge:
    """把 Azure Bot 的 conversation 映射到 wxo thread,并以文本增量的形式返回 agent 回复。"""

    def __init__(self, wxo: WxoClient, max_conversations: int = 10_000):
        self.wxo = wxo
        self._threads: OrderedDict[str, str] = OrderedDict()
        self._max = max_conversations

    async def ask(self, conversation_id: str, text: str) -> AsyncIterator[str]:
        thread_id = self._threads.get(conversation_id)
        async for delta in self.wxo.stream(text, thread_id):
            if delta.thread_id:
                self._threads[conversation_id] = delta.thread_id
                self._threads.move_to_end(conversation_id)
                while len(self._threads) > self._max:
                    self._threads.popitem(last=False)
            if delta.text:
                yield delta.text
