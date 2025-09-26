from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
from web3 import Web3
from web3.contract import Contract
import json
import requests
import asyncio
import aiohttp
from enum import Enum

class ProtocolType(Enum):
    UNISWAP_V2 = "uniswap_v2"
    UNISWAP_V3 = "uniswap_v3"
    SUSHISWAP = "sushiswap"
    CURVE = "curve"
    BALANCER = "balancer"
    AAVE = "aave"
    COMPOUND = "compound"
    YEARN = "yearn"
    CONVEX = "convex"

@dataclass
class TokenInfo:
    address: str
    symbol: str
    name: str
    decimals: int
    logo_url: Optional[str] = None

@dataclass
class PoolInfo:
    protocol: ProtocolType
    address: str
    tokens: List[TokenInfo]
    tvl: float
    apr: float
    apy: float
    volume_24h: float
    fees: float

@dataclass
class Position:
    protocol: ProtocolType
    pool_address: str
    token_id: Optional[int]  # For NFT positions like Uniswap V3
    liquidity: float
    token_amounts: Dict[str, float]
    unclaimed_fees: Dict[str, float]
    value_usd: float

class DeFiProtocolSDK:
    def __init__(self, web3_provider: str, private_key: Optional[str] = None):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        if private_key:
            self.account = self.w3.eth.account.from_key(private_key)
            self.address = self.account.address
        else:
            self.account = None
            self.address = None
            
        # 协议配置
        self.protocols = {
            ProtocolType.UNISWAP_V2: UniswapV2Handler(self.w3),
            ProtocolType.UNISWAP_V3: UniswapV3Handler(self.w3),
            ProtocolType.AAVE: AaveHandler(self.w3),
            ProtocolType.COMPOUND: CompoundHandler(self.w3),
            ProtocolType.CURVE: CurveHandler(self.w3),
        }
        
        self.token_list = {}
        self._load_common_tokens()

    def _load_common_tokens(self):
        """加载常用代币信息"""
        common_tokens = {
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": TokenInfo("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "WETH", "Wrapped Ether", 18),
            "0xA0b86a33E6441b0b5C4C1B89DfC2FbB4e0A0b26D": TokenInfo("0xA0b86a33E6441b0b5C4C1B89DfC2FbB4e0A0b26D", "USDT", "Tether USD", 6),
            "0xA0b86a33E6441b0b5C4C1B89DfC2FbB4e0A0b26D": TokenInfo("0xA0b86a33E6441b0b5C4C1B89DfC2FbB4e0A0b26D", "USDC", "USD Coin", 6),
            "0x6B175474E89094C44Da98b954EedeAC495271d0F": TokenInfo("0x6B175474E89094C44Da98b954EedeAC495271d0F", "DAI", "Dai Stablecoin", 18),
        }
        self.token_list.update(common_tokens)

    async def get_token_info(self, token_address: str) -> TokenInfo:
        """获取代币信息"""
        if token_address in self.token_list:
            return self.token_list[token_address]
        
        # ERC20 ABI
        erc20_abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
        ]
        
        contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)
        
        try:
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            
            token_info = TokenInfo(token_address, symbol, name, decimals)
            self.token_list[token_address] = token_info
            return token_info
            
        except Exception as e:
            print(f"获取代币信息失败: {e}")
            return TokenInfo(token_address, "UNKNOWN", "Unknown Token", 18)

    async def get_pools(self, protocol: ProtocolType, limit: int = 50) -> List[PoolInfo]:
        """获取协议池子信息"""
        handler = self.protocols.get(protocol)
        if not handler:
            raise ValueError(f"不支持的协议: {protocol}")
        
        return await handler.get_pools(limit)

    async def get_user_positions(self, user_address: Optional[str] = None) -> Dict[ProtocolType, List[Position]]:
        """获取用户在各协议的持仓"""
        if not user_address:
            user_address = self.address
            
        if not user_address:
            raise ValueError("需要提供用户地址")
        
        positions = {}
        for protocol_type, handler in self.protocols.items():
            try:
                user_positions = await handler.get_user_positions(user_address)
                if user_positions:
                    positions[protocol_type] = user_positions
            except Exception as e:
                print(f"获取 {protocol_type.value} 持仓失败: {e}")
        
        return positions

    async def swap_tokens(self, protocol: ProtocolType, token_in: str, token_out: str, 
                         amount_in: float, slippage: float = 0.5) -> str:
        """执行代币交换"""
        if not self.account:
            raise ValueError("需要私钥才能执行交易")
        
        handler = self.protocols.get(protocol)
        if not handler:
            raise ValueError(f"不支持的协议: {protocol}")
        
        return await handler.swap_tokens(token_in, token_out, amount_in, slippage, self.account)

    async def add_liquidity(self, protocol: ProtocolType, pool_address: str, 
                           token_amounts: Dict[str, float]) -> str:
        """添加流动性"""
        if not self.account:
            raise ValueError("需要私钥才能执行交易")
        
        handler = self.protocols.get(protocol)
        if not handler:
            raise ValueError(f"不支持的协议: {protocol}")
        
        return await handler.add_liquidity(pool_address, token_amounts, self.account)

    async def remove_liquidity(self, protocol: ProtocolType, position: Position, 
                              percentage: float = 100.0) -> str:
        """移除流动性"""
        if not self.account:
            raise ValueError("需要私钥才能执行交易")
        
        handler = self.protocols.get(protocol)
        if not handler:
            raise ValueError(f"不支持的协议: {protocol}")
        
        return await handler.remove_liquidity(position, percentage, self.account)

    async def lend_tokens(self, protocol: ProtocolType, token_address: str, amount: float) -> str:
        """借贷协议存款"""
        if not self.account:
            raise ValueError("需要私钥才能执行交易")
        
        if protocol not in [ProtocolType.AAVE, ProtocolType.COMPOUND]:
            raise ValueError("只支持AAVE和Compound借贷协议")
        
        handler = self.protocols.get(protocol)
        return await handler.supply(token_address, amount, self.account)

    async def borrow_tokens(self, protocol: ProtocolType, token_address: str, amount: float) -> str:
        """借贷协议借款"""
        if not self.account:
            raise ValueError("需要私钥才能执行交易")
        
        if protocol not in [ProtocolType.AAVE, ProtocolType.COMPOUND]:
            raise ValueError("只支持AAVE和Compound借贷协议")
        
        handler = self.protocols.get(protocol)
        return await handler.borrow(token_address, amount, self.account)

class ProtocolHandler:
    """协议处理器基类"""
    def __init__(self, w3: Web3):
        self.w3 = w3
    
    async def get_pools(self, limit: int) -> List[PoolInfo]:
        raise NotImplementedError
    
    async def get_user_positions(self, user_address: str) -> List[Position]:
        raise NotImplementedError
    
    async def swap_tokens(self, token_in: str, token_out: str, amount_in: float, 
                         slippage: float, account) -> str:
        raise NotImplementedError
    
    async def add_liquidity(self, pool_address: str, token_amounts: Dict[str, float], 
                           account) -> str:
        raise NotImplementedError
    
    async def remove_liquidity(self, position: Position, percentage: float, account) -> str:
        raise NotImplementedError

class UniswapV2Handler(ProtocolHandler):
    def __init__(self, w3: Web3):
        super().__init__(w3)
        self.router_address = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
        self.factory_address = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
        
        # Router ABI (简化)
        self.router_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMin", "type": "uint256"},
                    {"name": "path", "type": "address[]"},
                    {"name": "to", "type": "address"},
                    {"name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForTokens",
                "outputs": [{"name": "amounts", "type": "uint256[]"}],
                "type": "function"
            }
        ]
        
        self.router_contract = self.w3.eth.contract(
            address=self.router_address, 
            abi=self.router_abi
        )

    async def get_pools(self, limit: int) -> List[PoolInfo]:
        """通过The Graph API获取Uniswap V2池子"""
        query = """
        {
            pairs(first: %d, orderBy: reserveUSD, orderDirection: desc) {
                id
                token0 {
                    id
                    symbol
                    name
                    decimals
                }
                token1 {
                    id
                    symbol
                    name
                    decimals
                }
                reserveUSD
                volumeUSD
                totalSupply
            }
        }
        """ % limit
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2',
                json={'query': query}
            ) as response:
                data = await response.json()
                
                pools = []
                for pair in data['data']['pairs']:
                    token0 = TokenInfo(
                        pair['token0']['id'],
                        pair['token0']['symbol'],
                        pair['token0']['name'],
                        int(pair['token0']['decimals'])
                    )
                    token1 = TokenInfo(
                        pair['token1']['id'],
                        pair['token1']['symbol'],
                        pair['token1']['name'],
                        int(pair['token1']['decimals'])
                    )
                    
                    pool = PoolInfo(
                        protocol=ProtocolType.UNISWAP_V2,
                        address=pair['id'],
                        tokens=[token0, token1],
                        tvl=float(pair['reserveUSD']),
                        apr=0,  # 需要额外计算
                        apy=0,
                        volume_24h=float(pair['volumeUSD']),
                        fees=0.3  # Uniswap V2固定0.3%
                    )
                    pools.append(pool)
                
                return pools

    async def swap_tokens(self, token_in: str, token_out: str, amount_in: float, 
                         slippage: float, account) -> str:
        """执行Uniswap V2代币交换"""
        # 构建交换路径
        path = [token_in, token_out]
        
        # 获取代币信息
        token_in_info = await self._get_token_info(token_in)
        amount_in_wei = int(amount_in * (10 ** token_in_info.decimals))
        
        # 计算最小输出金额（考虑滑点）
        amounts_out = self.router_contract.functions.getAmountsOut(amount_in_wei, path).call()
        amount_out_min = int(amounts_out[-1] * (1 - slippage / 100))
        
        # 构建交易
        deadline = self.w3.eth.get_block('latest')['timestamp'] + 1200  # 20分钟
        
        transaction = self.router_contract.functions.swapExactTokensForTokens(
            amount_in_wei,
            amount_out_min,
            path,
            account.address,
            deadline
        ).build_transaction({
            'from': account.address,
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(account.address)
        })
        
        # 签名并发送交易
        signed_txn = account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return tx_hash.hex()

    async def get_user_positions(self, user_address: str) -> List[Position]:
        """获取用户Uniswap V2 LP持仓"""
        # 这需要通过The Graph或直接查询合约来实现
        # 简化实现
        return []

class AaveHandler(ProtocolHandler):
    def __init__(self, w3: Web3):
        super().__init__(w3)
        self.pool_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"  # AAVE V2
        
        # AAVE Pool ABI (简化)
        self.pool_abi = [
            {
                "inputs": [
                    {"name": "asset", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "onBehalfOf", "type": "address"},
                    {"name": "referralCode", "type": "uint16"}
                ],
                "name": "deposit",
                "outputs": [],
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "asset", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "interestRateMode", "type": "uint256"},
                    {"name": "referralCode", "type": "uint16"},
                    {"name": "onBehalfOf", "type": "address"}
                ],
                "name": "borrow",
                "outputs": [],
                "type": "function"
            }
        ]
        
        self.pool_contract = self.w3.eth.contract(
            address=self.pool_address,
            abi=self.pool_abi
        )

    async def supply(self, token_address: str, amount: float, account) -> str:
        """AAVE存款"""
        token_info = await self._get_token_info(token_address)
        amount_wei = int(amount * (10 ** token_info.decimals))
        
        transaction = self.pool_contract.functions.deposit(
            token_address,
            amount_wei,
            account.address,
            0  # referralCode
        ).build_transaction({
            'from': account.address,
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(account.address)
        })
        
        signed_txn = account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return tx_hash.hex()

    async def borrow(self, token_address: str, amount: float, account) -> str:
        """AAVE借款"""
        token_info = await self._get_token_info(token_address)
        amount_wei = int(amount * (10 ** token_info.decimals))
        
        transaction = self.pool_contract.functions.borrow(
            token_address,
            amount_wei,
            2,  # 可变利率
            0,  # referralCode
            account.address
        ).build_transaction({
            'from': account.address,
            'gas': 400000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(account.address)
        })
        
        signed_txn = account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return tx_hash.hex()

    async def get_pools(self, limit: int) -> List[PoolInfo]:
        """获取AAVE市场信息"""
        # 实现AAVE市场数据获取
        return []

    async def get_user_positions(self, user_address: str) -> List[Position]:
        """获取用户AAVE持仓"""
        # 实现用户持仓查询
        return []

class CompoundHandler(ProtocolHandler):
    """Compound协议处理器"""
    def __init__(self, w3: Web3):
        super().__init__(w3)
        # Compound相关合约地址和ABI
        pass

    async def get_pools(self, limit: int) -> List[PoolInfo]:
        return []

    async def get_user_positions(self, user_address: str) -> List[Position]:
        return []

class CurveHandler(ProtocolHandler):
    """Curve协议处理器"""
    def __init__(self, w3: Web3):
        super().__init__(w3)
        # Curve相关合约地址和ABI
        pass

    async def get_pools(self, limit: int) -> List[PoolInfo]:
        return []

    async def get_user_positions(self, user_address: str) -> List[Position]:
        return []

class UniswapV3Handler(ProtocolHandler):
    """Uniswap V3协议处理器"""
    def __init__(self, w3: Web3):
        super().__init__(w3)
        self.router_address = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
        self.position_manager_address = "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"

    async def get_pools(self, limit: int) -> List[PoolInfo]:
        return []

    async def get_user_positions(self, user_address: str) -> List[Position]:
        return []
