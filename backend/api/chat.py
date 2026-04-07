"""Chat API with SSE streaming support"""

import json
import asyncio
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agentscope.message import Msg

from models.request import ChatRequest
from agent.session import session_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_content_blocks(msg) -> list:
    """Extract content blocks from a message with broad compatibility.

    Handles various agentscope versions and message formats.
    """
    # 1. Try get_content_blocks() method first
    if hasattr(msg, 'get_content_blocks') and callable(msg.get_content_blocks):
        try:
            blocks = msg.get_content_blocks()
            if isinstance(blocks, list) and blocks:
                return blocks
        except Exception as e:
            logger.warning("get_content_blocks() failed: %s", e)

    # 2. Try .content attribute
    content = getattr(msg, 'content', None)
    if content is not None:
        if isinstance(content, str):
            return [{"type": "text", "text": content}]
        if isinstance(content, list):
            # Already a list of blocks (multimodal)
            return content
        if isinstance(content, dict):
            return [content]

    # 3. Fallback: stringify
    text = str(msg) if msg is not None else ""
    if text:
        return [{"type": "text", "text": text}]
    return []


async def event_generator(
    session_id: str,
    message: str,
    files: list,
    deep_research: bool
) -> AsyncGenerator[str, None]:
    """Generate SSE events from agent response"""

    # Track accumulated content to avoid duplicates
    accumulated_text = ""
    accumulated_thinking = ""
    done_sent = False

    try:
        # Get or create session
        session = session_manager.get_or_create(session_id, deep_research)

        # Build content blocks
        content_blocks = [{"type": "text", "text": message}]

        # Add file references
        for file_ref in files:
            if file_ref.type == "image":
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": file_ref.mime_type,
                        "data": file_ref.base64
                    }
                })
            elif file_ref.type == "video":
                content_blocks.append({
                    "type": "video",
                    "source": {
                        "type": "base64",
                        "media_type": file_ref.mime_type,
                        "data": file_ref.base64
                    }
                })

        # Create user message
        user_msg = Msg(
            name="user",
            content=content_blocks if len(content_blocks) > 1 else message,
            role="user"
        )

        # Add to agent memory
        session.agent.observe(user_msg)

        # Start agent reply as background task
        reply_task = asyncio.create_task(session.agent(user_msg))
        logger.info("[SSE] Started reply task for session %s", session_id)

        # Stream events from message queue
        while True:
            try:
                # Wait for message from queue with timeout
                try:
                    result = await asyncio.wait_for(
                        session.agent.msg_queue.get(),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    if reply_task.done():
                        logger.info("[SSE] Reply task done after timeout, ending stream")
                        break
                    logger.debug("[SSE] Queue timeout, still waiting...")
                    continue

                # --- Unpack result with compatibility handling ---
                msg = None
                last = False
                speech = None

                if isinstance(result, tuple):
                    if len(result) == 3:
                        msg, last, speech = result
                    elif len(result) == 2:
                        msg, last = result
                    elif len(result) == 1:
                        msg = result[0]
                    else:
                        logger.warning("[SSE] Unexpected tuple length %d", len(result))
                        msg = result[0] if result else None
                else:
                    # Single object (Msg or other)
                    msg = result

                if msg is None:
                    logger.debug("[SSE] Received None message, skipping")
                    continue

                logger.debug(
                    "[SSE] Received msg type=%s, last=%s, content_len=%s",
                    type(msg).__name__, last,
                    len(str(getattr(msg, 'content', ''))) if hasattr(msg, 'content') else '?'
                )

                # --- Process content blocks ---
                blocks = _extract_content_blocks(msg)

                for block in blocks:
                    if not isinstance(block, dict):
                        block = {"type": "text", "text": str(block)}

                    block_type = block.get("type", "text")

                    if block_type == "thinking":
                        thinking_content = block.get("thinking", "") or block.get("text", "")
                        if thinking_content and len(thinking_content) > len(accumulated_thinking):
                            delta = thinking_content[len(accumulated_thinking):]
                            accumulated_thinking = thinking_content
                            yield f"event: thinking\n"
                            yield f"data: {json.dumps({'thinking': delta}, ensure_ascii=False)}\n\n"
                    elif block_type == "text":
                        text_content = block.get("text", "") or block.get("content", "")
                        if text_content and len(text_content) > len(accumulated_text):
                            delta = text_content[len(accumulated_text):]
                            accumulated_text = text_content
                            yield f"event: text\n"
                            yield f"data: {json.dumps({'text': delta}, ensure_ascii=False)}\n\n"
                    elif block_type == "tool_use":
                        yield f"event: tool_use\n"
                        yield f"data: {json.dumps(block, ensure_ascii=False)}\n\n"
                    elif block_type == "tool_result":
                        yield f"event: tool_result\n"
                        yield f"data: {json.dumps(block, ensure_ascii=False)}\n\n"

                # --- Check if this is the final message ---
                if last:
                    done_sent = True
                    yield f"event: done\n"
                    yield f"data: {json.dumps({'session_id': session.session_id})}\n\n"
                    logger.info("[SSE] Stream completed (last=True) for session %s", session_id)
                    break

                # If reply_task finished and queue is empty, we're done
                if reply_task.done() and session.agent.msg_queue.empty():
                    logger.info("[SSE] Reply task done and queue empty, ending stream")
                    break

            except Exception as e:
                logger.error("[SSE] Error processing message: %s", e, exc_info=True)
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break

        # Ensure done event is always sent
        if not done_sent:
            # Check for any exception in the reply task
            if reply_task.done() and reply_task.exception():
                err = reply_task.exception()
                logger.error("[SSE] Reply task raised exception: %s", err)
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': str(err)})}\n\n"
            done_sent = True
            yield f"event: done\n"
            yield f"data: {json.dumps({'session_id': session_id})}\n\n"
            logger.info("[SSE] Sent final done event for session %s", session_id)

    except asyncio.CancelledError:
        logger.info("[SSE] Client disconnected for session %s", session_id)
        if 'session' in locals():
            try:
                session.agent.interrupt()
            except Exception:
                pass
    except Exception as e:
        logger.error("[SSE] Fatal error in event_generator: %s", e, exc_info=True)
        yield f"event: error\n"
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        if not done_sent:
            yield f"event: done\n"
            yield f"data: {json.dumps({'session_id': session_id})}\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Chat endpoint with SSE streaming

    Accepts a chat request and returns a streaming response from the agent.
    Supports multimodal input (text, images, video) and deep research mode.
    """
    return StreamingResponse(
        event_generator(
            session_id=request.session_id,
            message=request.message,
            files=request.files,
            deep_research=request.deep_research
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
