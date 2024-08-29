import socket
import time
import sys
from datetime import datetime

def udp_tracker(target_host, target_port, hex_data_packets, ipv6=False, show_timestamp=False):
    # 根据ipv6标志创建socket
    if ipv6:
        client = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    else:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 设置等待超时
    client.settimeout(5.0)

    # 循环发送数据包并接收响应
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

        # 指定每次发送后的等待时间，例如1秒
        time.sleep(1)

if __name__ == "__main__":
    # 命令行参数解析
    if len(sys.argv) < 3:
        print("Usage: python udp_tracker.py <domain> <port> [-s]")
        sys.exit(1)

    target_host = sys.argv[1]
    target_port = int(sys.argv[2])
    show_timestamp = '-s' in sys.argv

    # 定义固定的封包内容
    hex_data_packets = [
    #连接
    '000004172710198000000000334A0146',
    #开始
    '000004172710198000000001DEC0FCEE02D1D41ADD3B7634BEE7BE92E6E9D32AB009886A2D4243303139382DA30E9D2FABD2F95CA0BB21790000000000000000000000000000000000000000000000000000000200000000000096EC000000C82AE40000000004172710198000000001DEC0FCEE02D1D41ADD3B7634BEE7BE92E6E9D32AB009886A2D4243303139382DA30E9D2FABD2F95CA0BB21790000000000000000000000000000000000000000000000000000000200000000000096EC000000C82AE40000',
    #更新
    '0000041727101980000000010000000002D10D52AF979A108866A866AF404756E041EEE02D5554333533532D6CADFF4BEFFD09C416621DA50000000000000000000000005510000000000000000000000000000000000000EE033267FFFFFFFF5B5602382F616E6E6F756E6365202320ce6475706C6963617465206F66207564703A2F2F71672E6C6F727A6C2E67713A323731302F616E6E6F756E63650000041727101980000000010000001103339F4E45B7CDAFBCAC49E5E212300AE7CF33922D5554333533532D6CADFF4BEFFD09C416621DA50000000000000000000000000000400000000000000000000000000000000000EE033267FFFFFFFF5B5602382F616E6E6F756E63652023206475706C6963617465206F66207564703A2F2F71672E6C6F727A6C2E67713A323731302F616E6E6F756E6365ce'
    ]
    
    udp_tracker(target_host, target_port, hex_data_packets, show_timestamp=show_timestamp)
