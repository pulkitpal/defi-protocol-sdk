PROTOCOL_CONFIG = {
    'ethereum_mainnet': {
        'uniswap_v2': {
            'router': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
            'factory': '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
            'graph_endpoint': 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2'
        },
        'uniswap_v3': {
            'router': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
            'position_manager': '0xC36442b4a4522E871399CD717aBDD847Ab11FE88',
            'graph_endpoint': 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3'
        },
        'aave': {
            'pool': '0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9',
            'data_provider': '0x057835Ad21a177dbdd3090bB1CAE03EaCF78Fc6d'
        }
    }
}
