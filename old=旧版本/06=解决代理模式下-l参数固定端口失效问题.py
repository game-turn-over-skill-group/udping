import threading
import socket
import struct
import sys
import argparse
import time
import random

lock = threading.Lock()  # 初始化线程锁

def parse_proxy(proxy):
    """解析代理服务器"""
    print(f"Proxy parameter received for parsing: {proxy}")
    try:
        if proxy:
            if '://' not in proxy:
                raise ValueError("Invalid proxy format. Expected 'socks://host:port' or 'http://host:port'.")

            proxy_type, proxy_address = proxy.split('://', 1)

            # 检查是否是IPv6地址
            if proxy_address.startswith('['):
                end_bracket_index = proxy_address.find(']')
                if end_bracket_index == -1:
                    raise ValueError("Invalid IPv6 address format.")
                proxy_host = proxy_address[1:end_bracket_index]
                proxy_port = int(proxy_address[end_bracket_index + 2:])
            else:
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
    """解析ipv4+ipv6域名"""
    print(f"Attempting to resolve target host: {target_host}")
    ipv4_addr = None
    ipv6_addr = None

    try:
        ipv4_addr = socket.gethostbyname(target_host)
        print(f"Resolved IPv4 address: {ipv4_addr}")
    except socket.gaierror:
        print(f"Failed to resolve target host {target_host} as IPv4")

    try:
        ipv6_addr = socket.getaddrinfo(target_host, None, socket.AF_INET6)[0][4][0]
        print(f"Resolved IPv6 address: {ipv6_addr}")
    except socket.gaierror:
        print(f"Failed to resolve target host {target_host} as IPv6")

    return ipv4_addr, ipv6_addr

def generate_default_hex_data():
    """随机生成+改动结尾部分数据包"""
    default_hex_data = "000004172710198000000000" + ''.join(random.choice('0123456789ABCDEF') for _ in range(8))
    return default_hex_data

def get_buffer_size(hex_data):
    """根据数据包长度设置缓冲区大小"""
    if hex_data:
        max_packet_length = len(hex_data) // 2
        buffer_size = max_packet_length + 2
    else:
        buffer_size = 16 + 2
    return buffer_size

# ──────────────────────────────────────────────────────────────────────────────
# 手动 SOCKS5 UDP Associate 实现
# 彻底绕开 PySocks，原生支持 IPv4/IPv6 代理地址 + IPv4/IPv6 目标地址
# ──────────────────────────────────────────────────────────────────────────────

class Socks5UdpSocket:
    """
    手动完成 SOCKS5 UDP Associate 握手，封装成与 socket 相同接口的对象。
    支持代理地址为 IPv4 或 IPv6，目标地址也可以是 IPv4 / IPv6 / 域名。
    """
    def __init__(self, proxy_host, proxy_port, local_port=0, show_debug=False):
        self.show_debug = show_debug
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.local_port = local_port  # 0=随机，非0=用户指定固定端口
        self._tcp_ctrl = None    # TCP 控制连接（握手后必须保持，不能关闭）
        self._udp_sock = None    # 本地 UDP socket
        self._relay_addr = None  # 代理返回的 UDP 中继地址 (host, port)
        self._af = None          # 代理地址族

    def connect(self):
        """执行 SOCKS5 握手，建立 UDP Associate"""
        # 1. 自动判断代理地址族（支持 IPv4 / IPv6 / 域名）
        infos = socket.getaddrinfo(self.proxy_host, self.proxy_port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not infos:
            raise OSError(f"Cannot resolve proxy host: {self.proxy_host}")
        self._af, _, _, _, proxy_sockaddr = infos[0]

        # 2. 建立 TCP 控制连接
        self._tcp_ctrl = socket.socket(self._af, socket.SOCK_STREAM)
        self._tcp_ctrl.settimeout(5)
        self._tcp_ctrl.connect(proxy_sockaddr)
        #if self.show_debug:
        #    print(f"SOCKS5 TCP ctrl connected to {proxy_sockaddr}")

        # 3. 发送认证协商（只支持无认证 METHOD=0x00）
        self._tcp_ctrl.sendall(b'\x05\x01\x00')   # VER=5, NMETHODS=1, METHOD=无认证
        resp = self._tcp_ctrl.recv(2)
        if len(resp) < 2 or resp[0] != 0x05 or resp[1] != 0x00:
            raise OSError(f"SOCKS5 auth negotiation failed: {resp.hex()}")

        # 4. 发送 UDP ASSOCIATE 请求
        #    CMD=0x03, RSV=0x00, ATYP=0x01(IPv4), DST.ADDR=0.0.0.0, DST.PORT=0
        self._tcp_ctrl.sendall(b'\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00')
        # 读取完整回复（最短10字节，IPv6时22字节）
        reply = self._recv_exact(self._tcp_ctrl, 4)  # VER, REP, RSV, ATYP
        if reply[1] != 0x00:
            raise OSError(f"SOCKS5 UDP Associate refused, REP={reply[1]:#x}")

        atyp = reply[3]
        if atyp == 0x01:   # IPv4
            addr_raw = self._recv_exact(self._tcp_ctrl, 4)
            relay_ip = socket.inet_ntop(socket.AF_INET, addr_raw)
            relay_port = struct.unpack('!H', self._recv_exact(self._tcp_ctrl, 2))[0]
        elif atyp == 0x04: # IPv6
            addr_raw = self._recv_exact(self._tcp_ctrl, 16)
            relay_ip = socket.inet_ntop(socket.AF_INET6, addr_raw)
            relay_port = struct.unpack('!H', self._recv_exact(self._tcp_ctrl, 2))[0]
        elif atyp == 0x03: # 域名
            name_len = self._recv_exact(self._tcp_ctrl, 1)[0]
            relay_ip = self._recv_exact(self._tcp_ctrl, name_len).decode()
            relay_port = struct.unpack('!H', self._recv_exact(self._tcp_ctrl, 2))[0]
        else:
            raise OSError(f"Unknown ATYP in UDP Associate reply: {atyp}")

        # 代理有时返回 0.0.0.0 或 ::，表示"用代理自身 IP"
        if relay_ip in ('0.0.0.0', '::'):
            relay_ip = proxy_sockaddr[0]
        self._relay_addr = (relay_ip, relay_port)
        #if self.show_debug:
        #    print(f"SOCKS5 UDP relay at {self._relay_addr}")

        # 5. 创建本地 UDP socket，地址族跟随代理，支持固定端口（-l 参数）
        self._udp_sock = socket.socket(self._af, socket.SOCK_DGRAM)
        if self._af == socket.AF_INET:
            self._udp_sock.bind(('', self.local_port))
        else:
            self._udp_sock.bind(('::', self.local_port))
        self._tcp_ctrl.settimeout(None)
        return self

    @staticmethod
    def _recv_exact(sock, n):
        """从 TCP socket 精确读取 n 字节"""
        buf = b''
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise OSError("Connection closed while reading SOCKS5 reply")
            buf += chunk
        return buf

    def bind_port(self):
        """返回本地 UDP socket 实际绑定的端口"""
        return self._udp_sock.getsockname()[1]

    def settimeout(self, t):
        self._udp_sock.settimeout(t)

    def sendto(self, data, addr):
        """封装 SOCKS5 UDP 头部后发往中继"""
        dst_host, dst_port = addr
        # 构造 SOCKS5 UDP 请求头：RSV(2) + FRAG(1) + ATYP(1) + DST.ADDR + DST.PORT
        try:
            socket.inet_pton(socket.AF_INET6, dst_host)
            # IPv6 目标
            hdr = (b'\x00\x00\x00\x04'
                   + socket.inet_pton(socket.AF_INET6, dst_host)
                   + struct.pack('!H', dst_port))
        except OSError:
            try:
                socket.inet_pton(socket.AF_INET, dst_host)
                # IPv4 目标
                hdr = (b'\x00\x00\x00\x01'
                       + socket.inet_pton(socket.AF_INET, dst_host)
                       + struct.pack('!H', dst_port))
            except OSError:
                # 域名目标
                host_bytes = dst_host.encode()
                hdr = (b'\x00\x00\x00\x03'
                       + bytes([len(host_bytes)])
                       + host_bytes
                       + struct.pack('!H', dst_port))
        self._udp_sock.sendto(hdr + data, self._relay_addr)

    def recvfrom(self, bufsize):
        """接收并剥离 SOCKS5 UDP 头部，返回 (payload, (src_host, src_port))"""
        raw, _ = self._udp_sock.recvfrom(bufsize + 300)
        # RSV(2) + FRAG(1) + ATYP(1) = 4 bytes header
        atyp = raw[3]
        if atyp == 0x01:   # IPv4
            src_ip = socket.inet_ntop(socket.AF_INET, raw[4:8])
            src_port = struct.unpack('!H', raw[8:10])[0]
            payload = raw[10:]
        elif atyp == 0x04: # IPv6
            src_ip = socket.inet_ntop(socket.AF_INET6, raw[4:20])
            src_port = struct.unpack('!H', raw[20:22])[0]
            payload = raw[22:]
        elif atyp == 0x03: # 域名
            name_len = raw[4]
            src_ip = raw[5:5 + name_len].decode()
            src_port = struct.unpack('!H', raw[5 + name_len:7 + name_len])[0]
            payload = raw[7 + name_len:]
        else:
            raise OSError(f"Unknown ATYP in UDP response: {atyp}")
        return payload, (src_ip, src_port)

    def close(self):
        if self._udp_sock:
            try: self._udp_sock.close()
            except: pass
            self._udp_sock = None
        if self._tcp_ctrl:
            try: self._tcp_ctrl.close()
            except: pass
            self._tcp_ctrl = None


def check_proxy_connection(proxy_type, proxy_host, proxy_port, show_debug):
    """检测代理连接是否可用（支持IPv4/IPv6代理地址）"""
    try:
        addr_infos = socket.getaddrinfo(proxy_host, proxy_port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not addr_infos:
            print(f"Failed to resolve proxy host: {proxy_host}")
            return False
        af, _, _, _, sockaddr = addr_infos[0]
        test_socket = socket.socket(af, socket.SOCK_STREAM)
        test_socket.settimeout(5)
        test_socket.connect(sockaddr)
        test_socket.close()
        if show_debug:
            print(f"Proxy {proxy_host}:{proxy_port} is reachable.")
        return True
    except Exception as e:
        print(f"Failed to connect to proxy {proxy_host}:{proxy_port}: {e}")
        return False


def create_socket_and_bind(protocol, proxy_type, proxy_host, proxy_port, listen_port, show_debug):
    """创建socket并绑定"""
    #if show_debug:
        #print(f"\ncreate_socket_and_bind: protocol={protocol}, proxy_type={proxy_type}, "
        #      f"proxy_host={proxy_host}, proxy_port={proxy_port}, listen_port={listen_port}")
    try:
        if proxy_type == 'socks':
            #if show_debug:
            #    print("Creating SOCKS5 UDP socket (manual associate, supports IPv4/IPv6 proxy)...")
            client = Socks5UdpSocket(proxy_host, proxy_port, local_port=listen_port, show_debug=show_debug)
            client.connect()
            bind_port = client.bind_port()
        else:
            #if show_debug:
            #    print("Creating Direct Connection socket...")
            client = socket.socket(protocol, socket.SOCK_DGRAM)
            if listen_port == 0:
                listen_port = random.randint(1024, 65535)
            if protocol == socket.AF_INET6:
                #if show_debug:
                #    print("Binding as IPv6...")
                client.bind(("::", listen_port))
            else:
                #if show_debug:
                #    print("Binding as IPv4...")
                client.bind(("", listen_port))
            bind_port = client.getsockname()[1]

        #if show_debug:
            #print(f"Listening on port {bind_port}... ok")
        return client, bind_port
    except Exception as e:
        print(f"Failed to create/bind socket: {e}")
        return None, None


def warm_up_connection(client, resolved_target_host, target_port, proxy):
    """发送预热包打通路径，不等待回复（残留响应由发包前 clear_socket_buffer 丢弃）"""
    if not proxy:
        return
    try:
        client.sendto(bytes.fromhex(generate_default_hex_data()), (resolved_target_host, target_port))
    except Exception as e:
        print(f"Warm-up failed: {e}")


def clear_socket_buffer(client, show_debug, interval_time=1.0):
    """清理套接字缓冲区，避免数据包合并发送导致丢包问题"""
    try:
        client.settimeout(interval_time)
        while True:
            try:
                data, addr = client.recvfrom(4096)
                #if show_debug:
                #    print(f"Clearing socket buffer, discarded packet from: {addr} (size: {len(data)})")
            except socket.timeout:
                break
    except Exception as e:
        print(f"Error while clearing socket buffer: {e}")
    finally:
        client.settimeout(None)


def precise_sleep(duration):
    """精准型延迟控制器"""
    start = time.perf_counter()
    while time.perf_counter() - start < duration:
        pass


def print_statistics(resolved_host, target_port, stats):
    """打印 tcping 风格的统计摘要"""
    sent, succeeded, failed, times = stats['sent'], stats['succeeded'], stats['failed'], stats['times']
    fail_pct = (failed / sent * 100) if sent > 0 else 0.0
    print("")
    print(f"Ping statistics for {resolved_host}:{target_port}/udp")
    print(f"     {sent} probes sent.")
    if times:
        print(f"     {succeeded} successful, {failed} failed.  ({fail_pct:.2f}% fail)")
        print(f"Approximate trip times in milli-seconds:")
        print(f"     Minimum = {min(times):.3f}ms, Maximum = {max(times):.3f}ms, Average = {sum(times)/len(times):.3f}ms")
    else:
        print(f"     {succeeded} successful, {failed} failed.  ({fail_pct:.2f}% fail)")


def udp_tracker(target_host, target_port, custom_hex_data, is_custom_hex, listen_port,
                use_ipv4, use_ipv6, show_debug, continuous, count_limit, interval_time, wait_time, proxy):
    proxy_type, proxy_host, proxy_port = parse_proxy(proxy)

    # 设置缓冲区大小
    buffer_size = get_buffer_size(custom_hex_data if is_custom_hex else generate_default_hex_data())
    if show_debug:
        print(f"Buffer size set to: {buffer_size} bytes")

    # 检查代理可用性
    if proxy_host and proxy_port:
        if not check_proxy_connection(proxy_type, proxy_host, proxy_port, show_debug):
            print("Proxy connection check failed. Exiting.")
            return

    try:
        if use_ipv6:
            protocol = socket.AF_INET6
            ipv6_addr = resolve_target_host(target_host)[1]
            if not ipv6_addr:
                print(f"IPv6 address is not resolved for the target host {target_host}.")
                return
            resolved_target_host = ipv6_addr
        elif use_ipv4:
            protocol = socket.AF_INET
            ipv4_addr = resolve_target_host(target_host)[0]
            if not ipv4_addr:
                print(f"IPv4 address is not resolved for the target host {target_host}.")
                return
            resolved_target_host = ipv4_addr
        else:
            ipv4_addr, ipv6_addr = resolve_target_host(target_host)
            if ipv6_addr:
                protocol = socket.AF_INET6
                resolved_target_host = ipv6_addr
            elif ipv4_addr:
                protocol = socket.AF_INET
                resolved_target_host = ipv4_addr
            else:
                print(f"Failed to resolve target host {target_host} to a valid address.")
                return
    except Exception as e:
        print(f"Failed to resolve target host: {e}")
        return

    # fixed_port 必须在 create_socket_and_bind 之前判断
    # 因为调用后 listen_port 会从 0 变成实际分配的端口号
    fixed_port = (listen_port != 0)  # True=用户指定了-l固定端口，False=随机端口每4包切换

    # 创建并绑定套接字
    client, listen_port = create_socket_and_bind(protocol, proxy_type, proxy_host, proxy_port, listen_port, show_debug)
    if not client:
        return

    warm_up_connection(client, resolved_target_host, target_port, proxy)
    count = 0
    sent_packets = 0
    stats = {'sent': 0, 'succeeded': 0, 'failed': 0, 'times': []}

    if continuous:
        print("** Pinging continuously.  Press control-c to stop **")
    elif count_limit > 1:
        print(f"** Sending {count_limit} probes.  Press control-c to stop early **")

    try:
        while True:
            count += 1
            sent_packets += 1
            try:
                if is_custom_hex:
                    data = bytes.fromhex(custom_hex_data)
                else:
                    data = bytes.fromhex(generate_default_hex_data())

                if len(data) > buffer_size:
                    print(f"Warning: Data packet length {len(data)} exceeds buffer size {buffer_size}. Truncating...")
                    data = data[:buffer_size]

                with lock:
                    if show_debug:
                        print(f"\nSysTime: {time.strftime('%Y-%m-%d %H:%M:%S')}    Count: {count}")
                        print(f"Send to: ({resolved_target_host}, {target_port})‹ {listen_port} ›: {data.hex()}")

                    if proxy:
                        clear_socket_buffer(client, show_debug, interval_time)

                    client.sendto(data, (resolved_target_host, target_port))
                    stats['sent'] += 1
                    start_time = time.perf_counter()

                    # 自定义包无 tid 校验，直接接收第一个回包
                    # 默认包: 发送包 offset 12-16 是 transaction id
                    #         回包   offset  4-8  是 transaction id，校验匹配
                    # 这样可以过滤掉预热包/旧端口的残留回包，保证延迟计时准确
                    tid = data[12:16] if not is_custom_hex and len(data) >= 16 else None
                    try:
                        deadline = time.perf_counter() + wait_time
                        while True:
                            remaining = deadline - time.perf_counter()
                            if remaining <= 0:
                                raise socket.timeout()
                            client.settimeout(remaining)
                            response, addr = client.recvfrom(4096)
                            # 校验 transaction id：跳过不匹配的包（预热包回包、旧包等）
                            if tid is not None and len(response) >= 8 and response[4:8] != tid:
                                if show_debug:
                                    print(f"Skipped stale packet: tid={response[4:8].hex()} expected={tid.hex()}")
                                continue
                            break  # tid 匹配，接受此包
                        response_time = (time.perf_counter() - start_time) * 1000
                        stats['succeeded'] += 1
                        stats['times'].append(response_time)
                        if show_debug:
                            print(f"Recv from: {addr}‹ {response_time:.3f} ms ›: {response.hex()}")
                        else:
                            print(f"Probing {resolved_target_host}:{target_port}/udp - Reply from {addr[0]} - time={response_time:.3f}ms")
                    except socket.timeout:
                        stats['failed'] += 1
                        print(f"Probing {resolved_target_host}:{target_port}/udp - No response within {wait_time}s ‹ {listen_port} › timing out...")
                    except socket.error as e:
                        stats['failed'] += 1
                        print(f"Socket error while receiving: {e}")

            except Exception as e:
                print(f"Failed to send data: {e}")

            # 随机端口模式（未指定 -l）：每4包切换一次本地端口
            # 作用：绕过运营商对固定端口连续包的丢包策略
            if not fixed_port and sent_packets >= 4:
                client.close()
                with lock:
                    client, listen_port = create_socket_and_bind(protocol, proxy_type, proxy_host, proxy_port, 0, show_debug)
                    if not client:
                        return
                warm_up_connection(client, resolved_target_host, target_port, proxy)
                sent_packets = 0

            # 终止判断：非持续模式且已达到 count_limit 次
            if not continuous and count >= count_limit:
                break

            time.sleep(interval_time)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        client.close()
        print_statistics(resolved_target_host, target_port, stats)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDPing tool with proxy support")
    parser.add_argument("target_host", help="Target host to send UDP packets to")
    parser.add_argument("target_port", type=int, nargs='?', default=6969, help="Target port to send UDP packets to (default: 6969)")
    parser.add_argument("custom_hex_data", nargs='?', default=None, help="Hexadecimal data packets to send (default: generated with random HEX value)")
    parser.add_argument("-l", "--listen-port", type=int, default=0, help="Fixed local port (0 = random, rotates every 4 probes to avoid ISP throttling)")
    parser.add_argument("-4", "--ipv4", action="store_true", help="Use IPv4")
    parser.add_argument("-6", "--ipv6", action="store_true", help="Use IPv6")
    parser.add_argument('-s', '--show_debug', action='store_true', help="Enable debug mode to show detailed information")
    parser.add_argument("-c", "--continuous", action="store_true", help="Send packets continuously until Ctrl+C")
    parser.add_argument("-n", "--count", type=int, default=1, help="Number of probes to send (default: 1; -c overrides this)")
    parser.add_argument("-i", "--interval-time", type=float, default=1.0, help="Time interval between sending packets (in seconds)")
    parser.add_argument("-w", "--wait-time", type=float, default=2.0, help="Timeout duration for waiting for a response (in seconds)")
    parser.add_argument("-x", "--proxy", default="", help="Proxy setting (e.g., socks://host:port or http://host:port)")

    args = parser.parse_args()

    is_custom_hex = args.custom_hex_data is not None

    if args.ipv4 and args.ipv6:
        print("Error: Cannot use both IPv4 and IPv6 at the same time.")
        sys.exit(1)

    udp_tracker(
        target_host=args.target_host,
        target_port=args.target_port,
        custom_hex_data=args.custom_hex_data,
        is_custom_hex=is_custom_hex,
        listen_port=args.listen_port,
        use_ipv4=args.ipv4,
        use_ipv6=args.ipv6,
        show_debug=args.show_debug,
        continuous=args.continuous,
        count_limit=args.count if not args.continuous else 0,
        interval_time=args.interval_time,
        wait_time=args.wait_time,
        proxy=args.proxy
    )