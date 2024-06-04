import socket
import time
import datetime

# 目标主机的IP和UDP端口
target_host = "ipv4.rer.lol"
target_port = 2710

# 创建一个UDP socket
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# 设置等待超时为5秒
client.settimeout(5.0)

# 定义要发送的十六进制数据包列表
hex_data_packets = [
    #连接
    '000004172710198000000000334A0146',
    #开始
    '000004172710198000000001DEC0FCEE02D1D41ADD3B7634BEE7BE92E6E9D32AB009886A2D4243303139382DA30E9D2FABD2F95CA0BB21790000000000000000000000000000000000000000000000000000000200000000000096EC000000C82AE40000000004172710198000000001DEC0FCEE02D1D41ADD3B7634BEE7BE92E6E9D32AB009886A2D4243303139382DA30E9D2FABD2F95CA0BB21790000000000000000000000000000000000000000000000000000000200000000000096EC000000C82AE40000',
    #更新
    '0000041727101980000000010000000002D10D52AF979A108866A866AF404756E041EEE02D5554333533532D6CADFF4BEFFD09C416621DA50000000000000000000000005510000000000000000000000000000000000000EE033267FFFFFFFF5B5602382F616E6E6F756E6365202320ce6475706C6963617465206F66207564703A2F2F71672E6C6F727A6C2E67713A323731302F616E6E6F756E63650000041727101980000000010000001103339F4E45B7CDAFBCAC49E5E212300AE7CF33922D5554333533532D6CADFF4BEFFD09C416621DA50000000000000000000000000000400000000000000000000000000000000000EE033267FFFFFFFF5B5602382F616E6E6F756E63652023206475706C6963617465206F66207564703A2F2F71672E6C6F727A6C2E67713A323731302F616E6E6F756E6365ce'
]

# 使用循环来连续发送和接收
while True:
    for hex_data in hex_data_packets:
        byte_data = bytes.fromhex(hex_data)
        try:
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
            # 获取并格式化当前系统时间
            current_time = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
            print(current_time)  # 打印当前时间
            # tracker响应耗时?秒
            print(f"Received response from {addr} with delay of {delay} seconds")
        except socket.timeout:
            print("UDP request timed out")
        except Exception as e:
            print(f"An error occurred: {e}")

        # 指定每次发送后的等待时间，例如1秒
        sleep_time = 5.0
        time.sleep(sleep_time)
