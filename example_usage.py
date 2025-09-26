import asyncio
from src.defi_sdk import DeFiProtocolSDK, ProtocolType

async def main():
    # 初始化SDK
    sdk = DeFiProtocolSDK(
        web3_provider="https://mainnet.infura.io/v3/YOUR_INFURA_KEY",
        private_key="YOUR_PRIVATE_KEY"  # 可选，只有执行交易时才需要
    )

    print("=== DeFi协议SDK演示 ===\n")

    # 1. 获取Uniswap V2热门池子
    print("1. 获取Uniswap V2热门池子:")
    uniswap_pools = await sdk.get_pools(ProtocolType.UNISWAP_V2, limit=5)
    
    for pool in uniswap_pools:
        print(f"   {pool.tokens[0].symbol}/{pool.tokens[1].symbol}")
        print(f"   TVL: ${pool.tvl:,.2f}")
        print(f"   24h Volume: ${pool.volume_24h:,.2f}")
        print()

    # 2. 获取用户持仓（如果提供了私钥）
    if sdk.address:
        print("2. 用户持仓:")
        positions = await sdk.get_user_positions()
        
        for protocol, user_positions in positions.items():
            print(f"   {protocol.value}: {len(user_positions)} 个持仓")
            for pos in user_positions[:3]:  # 显示前3个
                print(f"      池子: {pos.pool_address[:10]}...")
                print(f"      价值: ${pos.value_usd:.2f}")

    # 3. 执行代币交换（示例，需要私钥）
    # if sdk.account:
    #     print("3. 执行代币交换:")
    #     tx_hash = await sdk.swap_tokens(
    #         ProtocolType.UNISWAP_V2,
    #         "0xA0b86a33E6441b0b5C4C1B89DfC2FbB4e0A0b26D",  # USDC
    #         "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
    #         100,  # 100 USDC
    #         slippage=0.5
    #     )
    #     print(f"   交易哈希: {tx_hash}")

    # 4. AAVE存款（示例，需要私钥）
    # if sdk.account:
    #     print("4. AAVE存款:")
    #     tx_hash = await sdk.lend_tokens(
    #         ProtocolType.AAVE,
    #         "0xA0b86a33E6441b0b5C4C1B89DfC2FbB4e0A0b26D",  # USDC
    #         1000  # 1000 USDC
    #     )
    #     print(f"   存款交易哈希: {tx_hash}")

if __name__ == "__main__":
    asyncio.run(main())

# portfolio_tracker.py
import asyncio
from src.defi_sdk import DeFiProtocolSDK, ProtocolType

class DeFiPortfolioTracker:
    def __init__(self, sdk: DeFiProtocolSDK):
        self.sdk = sdk
    
    async def get_portfolio_summary(self, user_address: str = None) -> dict:
        """获取投资组合总览"""
        positions = await self.sdk.get_user_positions(user_address)
        
        total_value = 0
        protocol_breakdown = {}
        
        for protocol, user_positions in positions.items():
            protocol_value = sum(pos.value_usd for pos in user_positions)
            total_value += protocol_value
            protocol_breakdown[protocol.value] = {
                'value': protocol_value,
                'positions': len(user_positions),
                'percentage': 0  # 将在下面计算
            }
        
        # 计算百分比
        for protocol_data in protocol_breakdown.values():
            protocol_data['percentage'] = (protocol_data['value'] / total_value) * 100 if total_value > 0 else 0
        
        return {
            'total_value_usd': total_value,
            'protocol_breakdown': protocol_breakdown,
            'position_count': sum(len(positions) for positions in positions.values())
        }
    
    def generate_report(self, portfolio_summary: dict) -> str:
        """生成投资组合报告"""
        report = f"""
