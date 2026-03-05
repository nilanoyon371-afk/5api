"""
HTTP Connection Pooling for Scrapers using httpx
Reuse connections for 50-100ms performance boost per request
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Singleton connection pool for all HTTP requests"""
    
    _instance: Optional['ConnectionPool'] = None
    _client: Optional[httpx.AsyncClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def client(self) -> httpx.AsyncClient:
        """
        Get or create httpx.AsyncClient with connection pooling
        
        Returns:
            Configured httpx.AsyncClient
        """
        if self._client is None or self._client.is_closed:
            # Connection pooling configuration
            limits = httpx.Limits(
                max_keepalive_connections=100, 
                max_connections=200, 
                keepalive_expiry=30.0
            )
            
            # Connection timeout configuration
            timeout = httpx.Timeout(
                30.0, 
                connect=10.0
            )
            
            # Create client
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            logger.info("Created httpx.AsyncClient connection pool with 200 concurrent connections")
        
        return self._client
    
    async def close(self):
        """Close the client and cleanup connections"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("Closed httpx.AsyncClient connection pool")


# Global pool instance
pool = ConnectionPool()


async def fetch_html(url: str, **kwargs) -> str:
    """
    Fetch HTML using shared connection pool
    
    Args:
        url: URL to fetch
        **kwargs: Additional arguments for client.get()
        
    Returns:
        HTML content
    """
    response = await pool.client.get(url, **kwargs)
    response.raise_for_status()
    return response.text


async def fetch_json(url: str, **kwargs) -> dict:
    """
    Fetch JSON using connection pool
    
    Args:
        url: URL to fetch
        **kwargs: Additional arguments for client.get()
        
    Returns:
        JSON data
    """
    response = await pool.client.get(url, **kwargs)
    response.raise_for_status()
    return response.json()


async def post_json(url: str, data: dict, **kwargs) -> dict:
    """
    POST JSON using connection pool
    
    Args:
        url: URL to post to
        data: JSON data to send
        **kwargs: Additional arguments for client.post()
        
    Returns:
        JSON response
    """
    response = await pool.client.post(url, json=data, **kwargs)
    response.raise_for_status()
    return response.json()
