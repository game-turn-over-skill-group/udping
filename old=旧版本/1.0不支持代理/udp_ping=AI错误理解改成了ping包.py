import socket
import time
import sys
from datetime import datetime

def udp_ping(target_host, target_port, ipv6=False, show_timestamp=False):
    # 根据ipv6标志创建socket
    if ipv6:
        client = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    else:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 设置等待超时
    client.settimeout(5.0)

    # 准备ping消息
    ping_message = 'ping'.encode()

    try:
        # 如果有-s参数，显示系统时间
        if show_timestamp:
            print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 发送ping消息
        start_time = time.time()
        client.sendto(ping_message, (target_host, target_port))
        
        # 接收响应
        data, addr = client.recvfrom(4096)
        end_time = time.time()
        
        # 计算延迟
        delay = end_time - start_time
        print(f"Received response from {addr} with delay of {delay:.6f} seconds")
    except socket.timeout:
        print("UDP request timed out")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    # 命令行参数解析
    if len(sys.argv) < 3:
        print("Usage: python udp_ping.py <domain> <port> [-s]")
        sys.exit(1)

    target_host = sys.argv[1]
    target_port = int(sys.argv[2])
    show_timestamp = '-s' in sys.argv

    # 默认使用IPv4
    ipv6 = False

    # 如果命令行中有udping6，使用IPv6
    if 'udping6' in sys.argv:
        ipv6 = True

    udp_ping(target_host, target_port, ipv6=ipv6, show_timestamp=show_timestamp)
