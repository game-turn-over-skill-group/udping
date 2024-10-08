import socket
import socks
import sys
import argparse
import time
import random

def parse_proxy(proxy):
    print(f"Proxy parameter received for parsing: {proxy}")
    try:
        if proxy:
            if '://' not in proxy:
                raise ValueError("Invalid proxy format. Expected 'socks://host:port' or 'http://host:port'.")

            proxy_type, proxy_address = proxy.split('://', 1)
            proxy_host, proxy_port = proxy_address.split(':', 1)
            proxy_port = int(proxy_port)

            if proxy_type not in ['socks', 'http']:
                raise ValueError("Unsupported proxy type: " + proxy_type)

            return proxy_type, proxy_host, proxy_port
        else:
            return None, None, None
    except ValueError as e:
        print(f"Invalid proxy format: {e}")
        sys.exit(1)

def resolve_target_host(target_host):
    print(f"Attempting to resolve target host: {target_host}")
    try:
        ipv4_addr = socket.gethostbyname(target_host)
        print(f"Resolved IPv4 address: {ipv4_addr}")
        return (ipv4_addr, None)
    except socket.gaierror:
        print(f"Failed to resolve target host {target_host} as IPv4")

    try:
        ipv6_addr = socket.getaddrinfo(target_host, None, socket.AF_INET6)[0][4][0]
        print(f"Resolved IPv6 address: {ipv6_addr}")
        return (None, ipv6_addr)
    except socket.gaierror:
        print(f"Failed to resolve target host {target_host} as IPv6")
        raise

def generate_default_hex_data():
    # 生成默认的数据包，其中最后8位为随机的HEX值
    default_hex_data = "000004172710198000000000" + ''.join(random.choice('0123456789ABCDEF') for _ in range(8))
    # print(f"Generated default hex data: {default_hex_data}")
    return default_hex_data

def udp_tracker(target_host, target_port, hex_data_packets, listen_port, ipv6, show_timecount, continuous, interval_time, wait_time, proxy):
    proxy_type, proxy_host, proxy_port = parse_proxy(proxy)

    try:
        ipv4_addr, ipv6_addr = resolve_target_host(target_host)
        resolved_target_host = ipv6 if ipv6 else ipv4_addr
    except Exception as e:
        print(f"Failed to resolve target host: {e}")
        return

    def create_socket_and_bind(listen_port):
        try:
            if proxy_type == 'socks':
            	# print("Creating SOCKS5 socket...")
                client = socks.socksocket(socket.AF_INET6 if ipv6 else socket.AF_INET, socket.SOCK_DGRAM)
                client.set_proxy(socks.SOCKS5, proxy_host, proxy_port)
            else:
            	# print("Creating regular socket...")
                client = socket.socket(socket.AF_INET6 if ipv6 else socket.AF_INET, socket.SOCK_DGRAM)
        except Exception as e:
        	print(f"Failed to create socket: {e}")
        	return

        try:
            if listen_port == 0:
                listen_port = random.randint(1024, 65535)  # Use a random port
            client.bind(("", listen_port))
            print(f"Listening on port {listen_port}... ", end="")
            if client.getsockname()[1] == listen_port:
                print("ok")
            else:
                print("fail")
            return client, listen_port
        except Exception as e:
            print(f"Failed to bind to port {listen_port}: {e}")
            client.close()
            return None, None

    # print("Socket is ready for data transfer")
    client, listen_port = create_socket_and_bind(listen_port)
    if not client:
        return

    count = 0
    sent_packets = 0

    try:
        if continuous:
            while True:
                for hex_data in hex_data_packets:
                    try:
                        count += 1
                        sent_packets += 1
                        # 在持续发送模式下生成随机的数据包
                        data = bytes.fromhex(generate_default_hex_data())
                        if show_timecount:
                            print(f"\nSysTime: {time.strftime('%Y-%m-%d %H:%M:%S')}    Count: {count}")
                        print(f"Send to: ({resolved_target_host}, {target_port})‹ {listen_port} ›: {data.hex()}")
                        client.sendto(data, (resolved_target_host, target_port))

                        start_time = time.time()
                        try:
                            client.settimeout(wait_time)
                            response, addr = client.recvfrom(4096)
                            end_time = time.time()
                            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                            print(f"Recv from: {addr}‹ {response_time:.2f} ms ›: {response.hex()}")
                        except socket.timeout:
                            print(f"No response within {wait_time} seconds, timing out...")
                        except socket.error as e:
                            print(f"Socket error while receiving: {e}")

                    except Exception as e:
                        print(f"Failed to send data: {e}")

                    # Check if it's time to switch ports
                    if sent_packets >= 4:
                        print("Switching ports after 4 requests...")
                        client.close()
                        client, listen_port = create_socket_and_bind(0)
                        if not client:
                            return
                        sent_packets = 0

                    time.sleep(interval_time)
        else:
            for hex_data in hex_data_packets:
                try:
                    count += 1
                    sent_packets += 1
                    data = bytes.fromhex(hex_data)
                    if show_timecount:
                        print(f"\nSysTime: {time.strftime('%Y-%m-%d %H:%M:%S')}    Count: {count}")
                    print(f"Send to: ({resolved_target_host}, {target_port})‹ {listen_port} ›: {data.hex()}")
                    client.sendto(data, (resolved_target_host, target_port))

                    start_time = time.time()
                    try:
                        client.settimeout(wait_time)
                        response, addr = client.recvfrom(4096)
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                        print(f"Recv from: {addr}‹ {response_time:.2f} ms ›: {response.hex()}")
                    except socket.timeout:
                        print(f"No response within {wait_time} seconds, timing out...")
                    except socket.error as e:
                        print(f"Socket error while receiving: {e}")

                except Exception as e:
                    print(f"Failed to send data: {e}")

                # Check if it's time to switch ports
                if sent_packets >= 4:
                    print("Switching ports after 4 requests...")
                    client.close()
                    client, listen_port = create_socket_and_bind(0)
                    if not client:
                        return
                    sent_packets = 0

                time.sleep(interval_time)
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # print("Closing socket...")
        client.close()
        # print("Socket closed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP Packet Sender")
    parser.add_argument("target_host", help="Target host to send UDP packets to")
    parser.add_argument("target_port", type=int, nargs='?', default=6969, help="Target port to send UDP packets to (default: 6969)")
    parser.add_argument("hex_data_packets", nargs='*', default=[generate_default_hex_data()], help="Hexadecimal data packets to send (default: generated with random HEX value)")
    parser.add_argument("-l", "--listen-port", type=int, default=0, help="Local port to listen for responses (0 for random port)")
    parser.add_argument("-4", "--ipv4", action="store_true", help="Use IPv4")
    parser.add_argument("-6", "--ipv6", action="store_true", help="Use IPv6")
    parser.add_argument("-s", "--show-TimeCount", action="store_true", help="Show system time and run count")
    parser.add_argument("-c", "--continuous", action="store_true", help="Send packets continuously")
    parser.add_argument("-i", "--interval-time", type=float, default=1.0, help="Time interval between sending packets (in seconds)")
    parser.add_argument("-w", "--wait-time", type=float, default=2.0, help="Timeout duration for waiting for a response (in seconds)")
    parser.add_argument("-x", "--proxy", default="", help="Proxy to use (e.g., socks://host:port)")

    args = parser.parse_args()

    udp_tracker(
        args.target_host,
        args.target_port,
        args.hex_data_packets,
        listen_port=args.listen_port,
        ipv6=args.ipv6,
        show_timecount=args.show_TimeCount,
        continuous=args.continuous,
        interval_time=args.interval_time,
        wait_time=args.wait_time,
        proxy=args.proxy
    )
