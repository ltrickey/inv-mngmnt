#!/usr/bin/env python3
"""
Mock API Gateway Server
Simulates API Gateway with API key authentication for local testing

Run with: python mock_api_gateway.py
Test with: curl -H "x-api-key: test-api-key-12345" http://localhost:8001/api/inventory/store1/12345?quantity=10
"""
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
import httpx
import os

# Configuration
MOCK_API_KEY = os.getenv("MOCK_API_KEY", "test-api-key-12345")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MOCK_PORT = int(os.getenv("MOCK_PORT", "8001"))

# Create mock API Gateway app
gateway_app = FastAPI(
    title="Mock API Gateway",
    description="Local mock of AWS API Gateway with API key authentication",
    version="1.0.0"
)

# Middleware to validate API key
@gateway_app.middleware("http")
async def validate_api_key(request: Request, call_next):
    """Validate x-api-key header like API Gateway does."""
    
    # Skip validation for docs and info endpoints
    if request.url.path in ["/", "/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)
    
    # Get API key from header
    api_key = request.headers.get("x-api-key")
    
    if not api_key:
        return JSONResponse(
            status_code=403,
            content={"message": "Forbidden"}
        )
    
    if api_key != MOCK_API_KEY:
        return JSONResponse(
            status_code=403,
            content={"message": "Forbidden"}
        )
    
    # API key is valid, proceed
    response = await call_next(request)
    return response


# Root endpoint (must be defined before catch-all proxy)
@gateway_app.get("/")
async def root():
    """Root endpoint with information about the mock gateway."""
    return {
        "service": "Mock API Gateway",
        "description": "Local development proxy with API key authentication",
        "api_key": {
            "header": "x-api-key",
            "example": MOCK_API_KEY,
            "note": "Use this API key in your requests"
        },
        "backend_url": BACKEND_URL,
        "example_requests": {
            "check_stock": f"curl -H 'x-api-key: {MOCK_API_KEY}' {BACKEND_URL}/api/inventory/store1/12345?quantity=10",
            "get_price": f"curl -H 'x-api-key: {MOCK_API_KEY}' {BACKEND_URL}/api/inventory/store1/12345/price",
            "deduct_single": f"curl -X PATCH -H 'x-api-key: {MOCK_API_KEY}' -H 'Content-Type: application/json' -d '{{\"quantity\": 5}}' {BACKEND_URL}/api/inventory/store1/12345",
            "deduct_batch": f"curl -X PATCH -H 'x-api-key: {MOCK_API_KEY}' -H 'Content-Type: application/json' -d '{{\"items\": [{{\"barcode\": \"12345\", \"quantity\": 2}}]}}' {BACKEND_URL}/api/inventory/store1"
        }
    }


# Proxy all requests to the backend (catch-all, must be defined AFTER specific routes)
@gateway_app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_request(request: Request, full_path: str):
    """Proxy all requests to the backend FastAPI service."""
    
    # Build backend URL
    backend_url = f"{BACKEND_URL}/{full_path}"
    if request.url.query:
        backend_url += f"?{request.url.query}"
    
    # Prepare headers (remove host header)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("x-api-key", None)  # Remove API key before forwarding
    
    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    # Forward request to backend
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=backend_url,
                headers=headers,
                content=body,
                follow_redirects=False
            )
            
            # Return backend response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
            
        except httpx.ConnectError:
            return JSONResponse(
                status_code=503,
                content={
                    "message": "Backend service unavailable",
                    "detail": f"Could not connect to {BACKEND_URL}"
                }
            )


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🔑 Mock API Gateway with API Key Authentication")
    print("=" * 60)
    print(f"\n📝 API Key: {MOCK_API_KEY}")
    print(f"🔗 Gateway URL: http://localhost:{MOCK_PORT}")
    print(f"🎯 Backend URL: {BACKEND_URL}")
    print(f"\n💡 Usage:")
    print(f"   curl -H 'x-api-key: {MOCK_API_KEY}' \\")
    print(f"        http://localhost:{MOCK_PORT}/api/inventory/store1/12345?quantity=10")
    print(f"\n✅ To change API key: export MOCK_API_KEY=your-key-here")
    print(f"✅ To change backend: export BACKEND_URL=http://other-host:port")
    print("\n" + "=" * 60 + "\n")
    
    uvicorn.run(
        gateway_app,
        host="0.0.0.0",
        port=MOCK_PORT,
        log_level="info"
    )
