import socket
import time
import sys
from datetime import datetime

def udp_tracker(target_host, target_port, hex_data_packets, ipv6=False, show_timestamp=False, interval=1):
    try:
        # 根据ipv6标志创建socket
        if ipv6:
            client = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        else:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 设置等待超时
        client.settimeout(5.0)

        # 循环发送数据包并接收响应
        while True:
            for hex_data in hex_data_packets:
                byte_data = bytes.fromhex(hex_data)
                try:
                    # 如果有-s参数，显示系统时间
                    if show_timestamp:
                        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    # 发送十六进制数据
                    client.sendto(byte_data, (target_host, target_port))
                    # 开始时间
                    start_time = time.time()
                    # 试图接收响应
                    data, addr = client.recvfrom(4096)
                    # 结束时间
                    end_time = time.time()
                    # 计算延迟
                    delay = end_time - start_time
                    print(f"Received response from {addr} with delay of {delay:.6f} seconds")
                except socket.timeout:
                    print("UDP request timed out")
                except Exception as e:
                    print(f"An error occurred: {e}")

            # 等待指定的时间间隔
            time.sleep(interval)
    finally:
        client.close()

def is_ipv6_address(hostname):
    try:
        # 解析主机名的地址信息
        addr_info = socket.getaddrinfo(hostname, None)
        # 检查是否存在 IPv6 地址信息
        for info in addr_info:
            if info[0] == socket.AF_INET6:
                return True
    except socket.gaierror:
        pass
    return False

def is_ipv4_address(hostname):
    try:
        # 解析主机名的地址信息
        addr_info = socket.getaddrinfo(hostname, None)
        # 检查是否存在 IPv4 地址信息
        for info in addr_info:
            if info[0] == socket.AF_INET:
                return True
    except socket.gaierror:
        pass
    return False

if __name__ == "__main__":
    # 命令行参数解析
    if len(sys.argv) < 3:
        print("Usage: python udp_tracker.py [-4 | -6] <domain> <port> [-s] [-t <interval>]")
        sys.exit(1)

    # 默认参数值
    ipv6 = False
    show_timestamp = False
    interval = 1  # 默认间隔为1秒

    # 解析命令行参数
    args = sys.argv[1:]
    while '-4' in args:
        ipv6 = False
        args.remove('-4')
    while '-6' in args:
        ipv6 = True
        args.remove('-6')
    while '-s' in args:
        show_timestamp = True
        args.remove('-s')
    if '-t' in args:
        index_t = args.index('-t')
        if index_t + 1 < len(args):
            try:
                interval = float(args[index_t + 1])
                args.pop(index_t)  # 移除 -t
                args.pop(index_t)  # 移除 <interval>
            except ValueError:
                print("Invalid argument for -t. Please provide a valid interval.")
                sys.exit(1)

    # 解析目标主机和端口
    target_host = args[0]
    target_port = int(args[1])

    # 定义固定的封包内容
    hex_data_packets = [
        # 连接
        '000004172710198000000000334A0146',
        # 开始
        '000004172710198000000001DEC0FCEE02D1D41ADD3B7634BEE7BE92E6E9D32AB009886A2D4243303139382DA30E9D2FABD2F95CA0BB21790000000000000000000000000000000000000000000000000000000200000000000096EC000000C82AE40000000004172710198000000001DEC0FCEE02D1D41ADD3B7634BEE7BE92E6E9D32AB009886A2D4243303139382DA30E9D2FABD2F95CA0BB21790000000000000000000000000000000000000000000000000000000200000000000096EC000000C82AE40000',
        # 更新
        '0000041727101980000000010000000002D10D52AF979A108866A866AF404756E041EEE02D5554333533532D6CADFF4BEFFD09C416621DA50000000000000000000000005510000000000000000000000000000000000000EE033267FFFFFFFF5B5602382F616E6E6F756E6365202320ce6475706C6963617465206F66207564703A2F2F71672E6C6F727A6C2E67713A323731302F616E6E6F756E63650000041727101980000000010000001103339F4E45B7CDAFBCAC49E5E212300AE7CF33922D5554333533532D6CADFF4BEFFD09C416621DA50000000000000000000000000000400000000000000000000000000000000000EE033267FFFFFFFF5B5602382F616E6E6F756E63652023206475706C6963617465206F66207564703A2F2F71672E6C6F727A6C2E67713A323731302F616E6E6F756E6365ce'
    ]

    # 执行UDP探测
    udp_tracker(target_host, target_port, hex_data_packets, ipv6=ipv6, show_timestamp=show_timestamp, interval=interval)
