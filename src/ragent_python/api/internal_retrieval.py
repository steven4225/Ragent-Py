from fastapi import APIRouter

from ragent_python.contracts.internal_api import InternalRetrievalRequestModel
from ragent_python.contracts.public_api import RetrievalResponseModel
from ragent_python.services.retrieval_service import execute_retrieval

router = APIRouter(prefix="/internal/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponseModel)
async def internal_retrieval_search(request: InternalRetrievalRequestModel) -> RetrievalResponseModel:
    return execute_retrieval(request)
