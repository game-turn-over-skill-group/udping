import socket
import socks
import sys
import argparse
import time
import random

def parse_proxy(proxy):
    """Parse the proxy format and return the type, host, and port."""
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
    """Attempt to resolve the target host as IPv4 and IPv6."""
    print(f"Attempting to resolve target host: {target_host}")
    try:
        # Try IPv4 resolution
        ipv4_addr = socket.gethostbyname(target_host)
        print(f"Resolved IPv4 address: {ipv4_addr}")
        return (ipv4_addr, None)
    except socket.gaierror:
        print(f"Failed to resolve target host {target_host} as IPv4")
        
    try:
        # Try IPv6 resolution
        ipv6_addr = socket.getaddrinfo(target_host, None, socket.AF_INET6)[0][4][0]
        print(f"Resolved IPv6 address: {ipv6_addr}")
        return (None, ipv6_addr)
    except socket.gaierror:
        print(f"Failed to resolve target host {target_host} as IPv6")
        raise

def udp_tracker(target_host, target_port, hex_data_packets, listen_port, ipv6, show_timestamp, continuous, wait_time, proxy):
    """Send and receive UDP packets using the specified proxy."""
    proxy_type, proxy_host, proxy_port = parse_proxy(proxy)

    # Resolve target host
    try:
        ipv4_addr, ipv6_addr = resolve_target_host(target_host)
        resolved_target_host = ipv6_addr if ipv6 else ipv4_addr
    except Exception as e:
        print(f"Failed to resolve target host: {e}")
        return

    # Create a SOCKS5 client socket if using SOCKS5 proxy
    try:
        if proxy_type == 'socks':
            print("Creating SOCKS5 socket...")
            client = socks.socksocket(socket.AF_INET6 if ipv6 else socket.AF_INET, socket.SOCK_DGRAM)
            client.set_proxy(socks.SOCKS5, proxy_host, proxy_port)
        else:
            print("Creating regular socket...")
            client = socket.socket(socket.AF_INET6 if ipv6 else socket.AF_INET, socket.SOCK_DGRAM)
    except Exception as e:
        print(f"Failed to create socket: {e}")
        return

    # Prepare to receive packets
    try:
        if listen_port == 0:
            listen_port = random.randint(1024, 65535)  # Use a random port
        client.bind(("", listen_port))
        print(f"Listening on port {listen_port}... ", end="")
        # Check if the socket is bound successfully
        if client.getsockname()[1] == listen_port:
            print("ok")
        else:
            print("fail")
    except Exception as e:
        print(f"Failed to bind to port {listen_port}: {e}")
        client.close()
        return

    try:
        print("Socket is ready for data transfer")
        while continuous:
            for hex_data in hex_data_packets:
                try:
                    data = bytes.fromhex(hex_data)
                    print(f"Sending data: {data.hex()}")  # Print data being sent
                    client.sendto(data, (resolved_target_host, target_port))
                    print(f"Data sent to {resolved_target_host}:{target_port}")

                    if show_timestamp:
                        print(f"Waiting for response... {time.strftime('%Y-%m-%d %H:%M:%S')}")

                    try:
                        response, addr = client.recvfrom(4096)
                        print(f"Received response from {addr}: {response.hex()}")  # Print received data
                    except socket.error as e:
                        print(f"Socket error while receiving: {e}")

                except Exception as e:
                    print(f"Failed to send data: {e}")

                time.sleep(wait_time)
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Closing socket...")
        client.close()
        print("Socket closed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP Packet Sender")
    parser.add_argument("target_host", help="Target host to send UDP packets to")
    parser.add_argument("target_port", type=int, help="Target port to send UDP packets to")
    parser.add_argument("hex_data_packets", nargs='+', help="Hexadecimal data packets to send")
    parser.add_argument("-l", "--listen-port", type=int, default=0, help="Local port to listen for responses (0 for random port)")
    parser.add_argument("-6", "--ipv6", action="store_true", help="Use IPv6")
    parser.add_argument("-t", "--show-timestamp", action="store_true", help="Show timestamp for each response")
    parser.add_argument("-c", "--continuous", action="store_true", help="Send packets continuously")
    parser.add_argument("-w", "--wait-time", type=float, default=1.0, help="Time to wait between packets")
    parser.add_argument("-x", "--proxy", default="", help="Proxy to use (e.g., socks://host:port)")

    args = parser.parse_args()
    
    udp_tracker(
        args.target_host,
        args.target_port,
        args.hex_data_packets,
        listen_port=args.listen_port,
        ipv6=args.ipv6,
        show_timestamp=args.show_timestamp,
        continuous=args.continuous,
        wait_time=args.wait_time,
        proxy=args.proxy
    )
