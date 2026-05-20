from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ragent_python.contracts.internal_api import InternalChatRequestModel
from ragent_python.contracts.public_api import ChatTurnResponseModel
from ragent_python.services.chat_service import build_chat_turn_response, iter_chat_stream_events

router = APIRouter(prefix="/internal/chat", tags=["chat"])


@router.post("/turn", response_model=ChatTurnResponseModel)
async def internal_chat_turn(request: InternalChatRequestModel) -> ChatTurnResponseModel:
    return build_chat_turn_response(request)


@router.post("/stream")
async def internal_chat_stream(request: InternalChatRequestModel) -> StreamingResponse:
    return StreamingResponse(
        iter_chat_stream_events(request),
        media_type="application/x-ndjson",
    )
