import socks
import socket
import binascii

def setup_proxy(proxy_url):
    try:
        proxy_type, proxy_host, proxy_port = proxy_url.split(':')
        proxy_type = proxy_type.lower()
        proxy_port = int(proxy_port)

        if proxy_type == 'socks5':
            socks.set_default_proxy(socks.SOCKS5, proxy_host, proxy_port)
        elif proxy_type == 'http':
            socks.set_default_proxy(socks.HTTP, proxy_host, proxy_port)
        else:
            raise ValueError("Unsupported proxy type")
        
        socket.socket = socks.socksocket
        print(f"Proxy set to {proxy_type}://{proxy_host}:{proxy_port}")
    except Exception as e:
        print(f"Error setting proxy: {e}")

def hex_to_bytes(hex_str):
    """Convert a hex string to bytes."""
    try:
        return binascii.unhexlify(hex_str)
    except binascii.Error as e:
        print(f"Hex to bytes conversion error: {e}")
        return None

def udp_tracker(target_host, target_port, hex_data_packets, proxy=None):
    if proxy:
        setup_proxy(proxy)

    try:
        print(f"Resolving target host: {target_host}")
        resolved_target_host = socket.getaddrinfo(target_host, None, socket.AF_INET)[0][4][0]
        print(f"Resolved target host: {resolved_target_host}")

        for hex_data in hex_data_packets:
            data = hex_to_bytes(hex_data)
            if data is None:
                print(f"Skipping invalid data: {hex_data}")
                continue

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(data, (resolved_target_host, target_port))
                print(f"Sent data: {data.hex()}")

                try:
                    response, addr = sock.recvfrom(4096)
                    print(f"Raw response: {response.hex()}")
                    print(f"Address: {addr}")

                except Exception as e:
                    print(f"Error receiving response: {e}")

    except socket.gaierror as e:
        print(f"Failed to resolve target host: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# 示例用法
proxy_url = "socks5:127.0.0.1:42416"  # 代理 URL
hex_data_packets = [
    # 连接
    '000004172710198000000000697CD3FA',
    # 添加更多的数据包内容（以 HEX 格式表示）
]
udp_tracker("ipv4.rer.lol", 6969, hex_data_packets, proxy=proxy_url)
