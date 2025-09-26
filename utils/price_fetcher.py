import aiohttp
from typing import Dict, List

class PriceFetcher:
    @staticmethod
    async def get_token_prices(token_addresses: List[str]) -> Dict[str, float]:
        """批量获取代币价格"""
        url = "https://api.coingecko.com/api/v3/simple/token_price/ethereum"
        params = {
            'contract_addresses': ','.join(token_addresses),
            'vs_currencies': 'usd'
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    return {addr: info.get('usd', 0) for addr, info in data.items()}
            except Exception as e:
                print(f"获取价格失败: {e}")
                return {}
