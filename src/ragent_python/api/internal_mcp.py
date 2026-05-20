from fastapi import APIRouter

from ragent_python.contracts.mcp import MCPExecuteRequestModel, MCPExecuteResponseModel
from ragent_python.services.mcp_service import execute_mcp_runtime

router = APIRouter(prefix="/internal/mcp", tags=["mcp"])


@router.post("/execute", response_model=MCPExecuteResponseModel)
async def internal_mcp_execute(request: MCPExecuteRequestModel) -> MCPExecuteResponseModel:
    return execute_mcp_runtime(request)
