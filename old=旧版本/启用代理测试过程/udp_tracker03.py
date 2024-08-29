import socks
import socket

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

def udp_tracker(target_host, target_port, proxy=None):
    if proxy:
        setup_proxy(proxy)

    try:
        print(f"Resolving target host: {target_host}")
        resolved_target_host = socket.getaddrinfo(target_host, None, socket.AF_INET6)[0][4][0]
        print(f"Resolved target host: {resolved_target_host}")

        # 创建并使用 socket 进行 UDP 请求
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as sock:
            data = b'\x00\x01'  # 示例数据
            sock.sendto(data, (resolved_target_host, target_port))

            try:
                response, addr = sock.recvfrom(4096)
                print(f"Raw response: {response}")
                print(f"Response from {addr}")
            except Exception as e:
                print(f"Error receiving response: {e}")

    except socket.gaierror as e:
        print(f"Failed to resolve target host: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# 示例用法
proxy_url = "socks5:127.0.0.1:42416"  # 代理 URL
udp_tracker("bt.rer.lol", 6969, proxy=proxy_url)
