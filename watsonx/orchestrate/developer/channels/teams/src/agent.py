import logging

from microsoft_agents.hosting.core import AgentApplication, MemoryStorage, TurnContext, TurnState

from .bridge import Bridge

logger = logging.getLogger(__name__)

FALLBACK_TEXT = "Sorry, something went wrong while contacting the agent."


def build_agent(connection_manager, bridge: Bridge) -> AgentApplication:
    """HTTP Messaging endpoint 使用的 AgentApplication:把消息转给 wxo,并用 SDK 的流式回复机制返回。"""
    agent = AgentApplication[TurnState](storage=MemoryStorage(), connection_manager=connection_manager)

    @agent.activity("message")
    async def on_message(context: TurnContext, _state: TurnState):
        activity = context.activity
        text = activity.text or ""
        if activity.recipient:
            text = activity.remove_mention_text(activity.recipient.id) or ""
        text = text.strip()
        if not text:
            return

        response = context.streaming_response
        response.queue_informative_update("Thinking...")
        try:
            async for chunk in bridge.ask(activity.conversation.id, text):
                response.queue_text_chunk(chunk)
        except Exception:
            logger.exception("agent call failed")
            response.queue_text_chunk(FALLBACK_TEXT)
        finally:
            await response.end_stream()

    return agent
