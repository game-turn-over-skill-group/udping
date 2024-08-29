import socket
import time
import sys
from datetime import datetime
import socks  # 需要安装 pysocks: pip install pysocks

def udp_tracker(target_host, target_port, hex_data_packets, listen_port=None, ipv6=False, show_timestamp=False, continuous=False, wait_time=1000, proxy=None):
    try:
        if proxy:
            proxy_type, proxy_host, proxy_port = parse_proxy(proxy)
            
            if proxy_type == 'socks':
                if ipv6:
                    client = socks.socksocket(socket.AF_INET6, socket.SOCK_DGRAM)
                else:
                    client = socks.socksocket(socket.AF_INET, socket.SOCK_DGRAM)
                client.set_proxy(socks.SOCKS5, proxy_host, proxy_port)
            elif proxy_type == 'http':
                print("HTTP proxies do not support UDP.")
                return
            else:
                print(f"Unsupported proxy type: {proxy_type}")
                return
        else:
            if ipv6:
                client = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            else:
                client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        if listen_port:
            bind_address = ("::", listen_port) if ipv6 else ("0.0.0.0", listen_port)
            client.bind(bind_address)

        client.settimeout(wait_time / 1000)
        
        try:
            resolved_target_host = socket.getaddrinfo(target_host, None, socket.AF_INET6 if ipv6 else socket.AF_INET)[0][4][0]
        except socket.gaierror as e:
            print(f"Failed to resolve target host {target_host}: {e}")
            return

        for i, hex_data in enumerate(hex_data_packets):
            byte_data = bytes.fromhex(hex_data)
            try:
                if show_timestamp:
                    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                client.sendto(byte_data, (resolved_target_host, target_port))
                start_time = time.time()
                data, addr = client.recvfrom(4096)
                end_time = time.time()
                delay = (end_time - start_time) * 1000
                print(f"Type[{i+1:02d}]: Received response from {addr} with delay of {delay:.6f} ms")
            except socket.timeout:
                local_port = client.getsockname()[1]
                print(f"UDP request timed out (Target IP: {resolved_target_host}, Target Port: {target_port}, Local Port: {local_port})")
            except Exception as e:
                print(f"An error occurred: {e}")

            time.sleep(wait_time / 1000)

            client.close()  # 关闭socket

            if not continuous:
                break

    finally:
        client.close()


def parse_proxy(proxy):
    try:
        if '://' not in proxy:
            raise ValueError("Invalid proxy format. Expected 'socks://host:port' or 'http://host:port'.")
        proxy_type, proxy_address = proxy.split('://', 1)
        proxy_host, proxy_port = proxy_address.split(':', 1)
        proxy_port = int(proxy_port)
        if proxy_type not in ['socks', 'http']:
            raise ValueError("Unsupported proxy type: " + proxy_type)
        return proxy_type, proxy_host, proxy_port
    except ValueError as e:
        print(f"Invalid proxy format: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python udping.py [-4 | -6] <domain> [<port>] [-s] [-t <wait_time_ms>] [-p <listen_port>] [-x <proxy>]")
        sys.exit(1)

    ipv6 = '-6' in sys.argv
    if '-4' in sys.argv:
        ipv6 = False
    if '-6' in sys.argv:
        sys.argv.remove('-6')
    if '-4' in sys.argv:
        sys.argv.remove('-4')
    
    target_host = sys.argv[1]
    target_port = int(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[2].isdigit() else 6969
    show_timestamp = '-s' in sys.argv
    continuous = '-t' in sys.argv

    wait_time = 1000
    if '-t' in sys.argv:
        wait_time_index = sys.argv.index('-t') + 1
        if wait_time_index < len(sys.argv):
            wait_time = int(sys.argv[wait_time_index])

    listen_port = None
    if '-p' in sys.argv:
        listen_port_index = sys.argv.index('-p') + 1
        if listen_port_index < len(sys.argv):
            listen_port = int(sys.argv[listen_port_index])

    proxy = None
    if '-x' in sys.argv:
        proxy_index = sys.argv.index('-x') + 1
        if proxy_index < len(sys.argv):
            proxy = sys.argv[proxy_index]

    hex_data_packets = [
        '000004172710198000000000697CD3FA',
        '000004172710198000000000A9A2AED7CE3C3A390079B8F000000001CC7D6498E6B8A29AEFFE14D796B17A360CFA9F31E8DD4C1C2D4243303230382DE4BFAEE5BDBCE5BE97E69BBC000000000000000000000000000000000000000000000000000000020000000024895A510000006456CF0000CE3C3A390079B8F000000001E3CF064031DF3ECFA5A14EF7AE136FC94BD9AAD4BD90D9602D4243303230382DE4BFAEE5BDBCE5BE97E69BBC00000000000000000000000000000000000000000000000000000002000000007409DD100000006456CF0000',
        '00000417271019800000000026D817FBCA32314D0079AD3C00000001ABC7DE4931DF3ECFA5A14EF7AE136FC94BD9AAD4BD90D9602D4243303230382DE4BFAEE5BDBCE5BE97E69BBC00000000000000000000000000000000000000000000000000000002000000007409DD100000006456CF0000CA32314D0079AD3C00000001ABC7DE4931DF3ECFA5A14EF7AE136FC94BD9AAD4BD90D9602D4243303230382DE4BFAEE5BDBCE5BE97E69BBC00000000000000000000000000000000000000000000000000000002000000007409DD100000006456CF0000',
        '000004172710198000000000211B6D4AE919337B0079B9DB000000013CEFD99731DF3ECFA5A14EF7AE136FC94BD9AAD4BD90D9602D4243303230382DE4BFAEE5BDBCE5BE97E69BBC00000000000000000000000000000000000000000000000000000003000000007409DD100000000056CF0000E919337B0079B9DB000000012515A249E6B8A29AEFFE14D796B17A360CFA9F31E8DD4C1C2D4243303230382DE4BFAEE5BDBCE5BE97E69BBC000000000000000000000000000000000000000000000000000000030000000024895A510000000056CF0000'
    ]

    udp_tracker(target_host, target_port, hex_data_packets, listen_port=listen_port, ipv6=ipv6, show_timestamp=show_timestamp, continuous=continuous, wait_time=wait_time, proxy=proxy)
