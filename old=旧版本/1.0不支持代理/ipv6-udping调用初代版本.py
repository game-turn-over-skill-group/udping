# udping6.py (IPv6)
from udp_tracker import udp_tracker

# 定义IPv6专用的数据包
hex_data_packets_ipv6 = [
    # 这里放置IPv6数据包十六进制字符串
]

# 在这里调用udp_tracker函数，确保修改为适当的主机和端口，并设置ipv6=True
udp_tracker('example.com', 1234, hex_data_packets_ipv6, ipv6=True)
