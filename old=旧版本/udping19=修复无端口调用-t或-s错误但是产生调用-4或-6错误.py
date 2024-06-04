import socket
import time
import sys
from datetime import datetime

def udp_tracker(target_host, target_port, hex_data_packets, ipv6=False, show_timestamp=False, continuous=False, wait_time=1000):
    try:
        # 根据ipv6标志创建socket
        if ipv6:
            client = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        else:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 设置等待超时
        client.settimeout(5.0)

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
            
        # 检测是否需要连续执行
        if continuous:
            udp_tracker(target_host, target_port, hex_data_packets, ipv6=ipv6, show_timestamp=show_timestamp, continuous=continuous, wait_time=wait_time)
            
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
        print("Usage: python udp_tracker.py [-4 | -6] <domain> [<port>] [-s] [-t <wait_time_ms>]")
        sys.exit(1)

    # 检查第2个参数 端口号 是否为空/不为整数, 如果是添加6969为默认端口号
    if len(sys.argv) < 3 or not sys.argv[2].isdigit():
        try:
            # 尝试将第三个参数解析为整数
            int(sys.argv[2])
        except (IndexError, ValueError):
            # 如果出现异常或者第三个参数不存在或者无法解析为整数，则添加默认端口号6969
            sys.argv.insert(2, '6969')


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

    # 定义 解析命令行参数
    target_host = sys.argv[1]
    target_port = int(sys.argv[2]) if len(sys.argv) >= 3 else 6969
    show_timestamp = '-s' in sys.argv
    continuous = '-t' in sys.argv

    # 检查是否指定了自定义等待时间
    wait_time = 1000  # 默认等待时间为1000毫秒
    wait_time_index = sys.argv.index('-t') + 1 if '-t' in sys.argv and len(sys.argv) > sys.argv.index('-t') + 1 else -1
    if wait_time_index != -1 and wait_time_index < len(sys.argv):
        wait_time = int(sys.argv[wait_time_index])

    # 定义固定的封包内容
    hex_data_packets = [
        # 连接
        '00000417271019800000000041A6C6CB',
        # 开始
        '000004172710198000000001C545E3AD64EA2E58D51C699A65A126E41FBFE506BB3BD3AC2D4243303230362DF6B548CD730F0187D098C753000000000000000000000000000000000000000000000000000000020000000000006AA1000000C84E480000000004172710198000000001C545E3AD64EA2E58D51C699A65A126E41FBFE506BB3BD3AC2D4243303230362DF6B548CD730F0187D098C753000000000000000000000000000000000000000000000000000000020000000000006AA1000000C84E480000',
        # 更新
        '000004172710198000000001C545E3AD64EA2E58D51C699A65A126E41FBFE506BB3BD3AC2D4243303230362DF6B548CD730F0187D098C753000000000000000000000000000000000000000000000000000000000000000000006AA1000000C84E480000000004172710198000000001C545E3AD64EA2E58D51C699A65A126E41FBFE506BB3BD3AC2D4243303230362DF6B548CD730F0187D098C753000000000000000000000000000000000000000000000000000000000000000000006AA1000000C84E480000',
        # 断开
        '000004172710198000000001C545E3AD64EA2E58D51C699A65A126E41FBFE506BB3BD3AC2D4243303230362DF6B548CD730F0187D098C753000000000000000000000000000000000000000000000000000000030000000000006AA1000000C84E480000000004172710198000000001C545E3AD64EA2E58D51C699A65A126E41FBFE506BB3BD3AC2D4243303230362DF6B548CD730F0187D098C753000000000000000000000000000000000000000000000000000000030000000000006AA1000000C84E480000'
    ]

    # 执行UDP探测
    udp_tracker(target_host, target_port, hex_data_packets, ipv6=ipv6, show_timestamp=show_timestamp, continuous=continuous, wait_time=wait_time)
