import socket
import time
import sys
from datetime import datetime

def udp_tracker(target_host, target_port, hex_data_packets, listen_port=None, ipv6=False, show_timestamp=False, continuous=False, wait_time=1000):
    try:
        while True:
            # 根据ipv6标志创建socket
            if ipv6:
                client = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            else:
                client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 如果设置了固定监听端口，绑定到该端口
            if listen_port:
                if ipv6:
                    client.bind(("::", listen_port))
                else:
                    client.bind(("0.0.0.0", listen_port))

            # 设置等待超时
            client.settimeout(wait_time / 1000)

            # 循环发送数据包并接收响应
            for i, hex_data in enumerate(hex_data_packets):
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
                    delay = (end_time - start_time) * 1000  # 将延迟从秒转换为毫秒
                    # 打印数据包类型或编号以及反馈信息
                    print(f"Type[{i+1:02d}]: Received response from {addr} with delay of {delay:.6f} ms")
                except socket.timeout:
                    print("UDP request timed out")
                except Exception as e:
                    print(f"An error occurred: {e}")

                # 指定每次发送后的等待时间
                time.sleep(wait_time / 1000)  # 将等待时间从毫秒转换为秒

            # 关闭当前的socket
            client.close()

            # 检测是否需要连续执行
            if not continuous:
                break
            
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
    if len(sys.argv) < 2:
        print("Usage: python udp_tracker.py [-4 | -6] <domain> [<port>] [-s] [-t <wait_time_ms>] [-p <listen_port>]")
        sys.exit(1)

    # 检查是否有 -4 或 -6 选项, 以手动指定IPv4或IPv6 (包含删除参数避免下面定义错误)
    ipv6 = False
    if '-4' in sys.argv:
        ipv6 = False
        sys.argv.remove('-4')
    elif '-6' in sys.argv:
        ipv6 = True
        sys.argv.remove('-6')
    else:
        # 如果未指定 -4 或 -6 参数，则根据域名的类型选择 IP 模式
        if is_ipv4_address(sys.argv[1]):
            ipv6 = False
        elif is_ipv6_address(sys.argv[1]):
            ipv6 = True

    # 定义解析命令行参数
    target_host = sys.argv[1]
    
    # 检查第2个参数是否为整数，如果不是或为空，使用默认端口号6969
    target_port = int(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[2].isdigit() else 6969
    
    show_timestamp = '-s' in sys.argv
    continuous = '-t' in sys.argv

    # 检查是否指定了自定义等待时间
    wait_time = 1000  # 默认等待时间为1000毫秒
    wait_time_index = sys.argv.index('-t') + 1 if '-t' in sys.argv and len(sys.argv) > sys.argv.index('-t') + 1 else -1
    if wait_time_index != -1 and wait_time_index < len(sys.argv):
        wait_time = int(sys.argv[wait_time_index])
    
    # 检查是否指定了监听端口
    listen_port = None
    listen_port_index = sys.argv.index('-p') + 1 if '-p' in sys.argv and len(sys.argv) > sys.argv.index('-p') + 1 else -1
    if listen_port_index != -1 and listen_port_index < len(sys.argv):
        listen_port = int(sys.argv[listen_port_index])

    # 定义固定的封包内容
    hex_data_packets = [
        # 连接
        '000004172710198000000000697CD3FA',
        # 开始
        '000004172710198000000000A9A2AED7CE3C3A390079B8F000000001CC7D6498E6B8A29AEFFE14D796B17A360CFA9F31E8DD4C1C2D4243303230382DE4BFAEE5BDBCE5BE97E69BBC000000000000000000000000000000000000000000000000000000020000000024895A510000006456CF0000CE3C3A390079B8F000000001E3CF064031DF3ECFA5A14EF7AE136FC94BD9AAD4BD90D9602D4243303230382DE4BFAEE5BDBCE5BE97E69BBC00000000000000000000000000000000000000000000000000000002000000007409DD100000006456CF0000',
        # 更新
        '00000417271019800000000026D817FBCA32314D0079AD3C00000001ABC7DE4931DF3ECFA5A14EF7AE136FC94BD9AAD4BD90D9602D4243303230382DE4BFAEE5BDBCE5BE97E69BBC00000000000000000000000000000000000000000000000000000002000000007409DD100000006456CF0000CA32314D0079AD3C00000001ABC7DE4931DF3ECFA5A14EF7AE136FC94BD9AAD4BD90D9602D4243303230382DE4BFAEE5BDBCE5BE97E69BBC00000000000000000000000000000000000000000000000000000002000000007409DD100000006456CF0000',
        # 断开
        '000004172710198000000000211B6D4AE919337B0079B9DB000000013CEFD99731DF3ECFA5A14EF7AE136FC94BD9AAD4BD90D9602D4243303230382DE4BFAEE5BDBCE5BE97E69BBC00000000000000000000000000000000000000000000000000000003000000007409DD100000000056CF0000E919337B0079B9DB000000012515A249E6B8A29AEFFE14D796B17A360CFA9F31E8DD4C1C2D4243303230382DE4BFAEE5BDBCE5BE97E69BBC000000000000000000000000000000000000000000000000000000030000000024895A510000000056CF0000'
    ]

    # 执行UDP探测
    udp_tracker(target_host, target_port, hex_data_packets, listen_port=listen_port, ipv6=ipv6, show_timestamp=show_timestamp, continuous=continuous, wait_time=wait_time)
