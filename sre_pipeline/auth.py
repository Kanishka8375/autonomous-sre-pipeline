import os
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key_header: str = Security(api_key_header)) -> str:
    expected_api_key = os.getenv("SRE_API_KEY")
    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SRE_API_KEY not configured on server",
        )
    if api_key_header != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )
    return api_key_header
