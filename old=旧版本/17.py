import socket
import socks
import sys
import argparse
import time

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

def udp_tracker(target_host, target_port, hex_data_packets, listen_port, ipv6, show_timestamp, continuous, wait_time, proxy):
    """Send and receive UDP packets using the specified proxy."""
    proxy_type, proxy_host, proxy_port = parse_proxy(proxy)

    # Resolve target host
    try:
        print(f"Attempting to resolve target host: {target_host}")
        if ipv6:
            resolved_target_host = socket.getaddrinfo(target_host, None, socket.AF_INET6)[0][4][0]
        else:
            resolved_target_host = socket.gethostbyname(target_host)
        print(f"Resolved target host: {resolved_target_host}")
    except socket.gaierror as e:
        print(f"Failed to resolve target host {target_host}: {e}")
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
            listen_port = 12345
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
        while continuous:
            for hex_data in hex_data_packets:
                try:
                    data = bytes.fromhex(hex_data)
                    print(f"Sending data: {data.hex()}")  # Print data being sent
                    client.sendto(data, (resolved_target_host, target_port))
                    print(f"Data sent to {resolved_target_host}:{target_port}")
                except Exception as e:
                    print(f"Failed to send data: {e}")
                    continue
                
                if show_timestamp:
                    print(f"Waiting for response... {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                try:
                    response, addr = client.recvfrom(4096)
                    print(f"Received response from {addr}: {response.hex()}")  # Print received data
                except socket.error as e:
                    print(f"Socket error while receiving: {e}")
                    
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
    parser.add_argument("-l", "--listen-port", type=int, default=0, help="Local port to listen for responses")
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
