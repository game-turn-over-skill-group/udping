#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <netdb.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <cstddef> // 添加此头文件

#ifdef _WIN32
#include <ws2tcpip.h>
#pragma comment(lib, "Ws2tcpip.lib")
#else
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#endif

#define BUFFER_SIZE 1024

// 函数声明
int create_socket_and_bind(int protocol, const std::string& proxy_type, 
                        const std::string& proxy_host, int proxy_port, 
                        int listen_port, bool show_debug);

// 解析命令行参数
bool parse_args(int argc, char* argv[], std::string& proxy_type,
                std::string& proxy_host, int& proxy_port,
                std::string& target_host, int& target_port,
                int& buffer_size, int& protocol, bool& show_debug);

// 解析 IP 地址
bool parse_ip(const std::string& ip_str, struct in_addr* addr);
bool parse_ipv6(const std::string& ip_str, struct in6_addr* addr);

// 检查代理连接
bool check_proxy_connection(const std::string& proxy_type,
                            const std::string& proxy_host, int proxy_port);

// 创建 UDP 套接字并绑定端口
int create_socket_and_bind(int protocol, const std::string& proxy_type,
                        const std::string& proxy_host, int proxy_port, 
                        int listen_port, bool show_debug) {
    int sockfd = -1;
    int val = 1;
    sockaddr_in addr;

    // 创建 UDP 套接字
    sockfd = socket(protocol, SOCK_DGRAM, 0);
    if (sockfd == -1) {
        std::cerr << "Failed to create socket: " << strerror(errno) << std::endl;
        return -1;
    }

    if (show_debug) {
        std::cout << "create_socket_and_bind: protocol: " << protocol 
                  << ", proxy_type: " << proxy_type << ", proxy_host: " 
                  << proxy_host << ", proxy_port: " << proxy_port
                  << ", listen_port: " << listen_port << std::endl;
    }

    // 设置代理
    if (proxy_type == "socks") {
        if (show_debug) {
            std::cout << "Creating SOCKS5 Proxy socket..." << std::endl;
        }

        // TODO: 使用 `socks` 库设置代理，并连接到目标地址
        // 使用适当的 `socks` 库的 UDP 连接方法
        // ...

    } else {
        if (show_debug) {
            std::cout << "Creating Direct Connection socket..." << std::endl;
        }
    }

    // 绑定端口
    if (listen_port != 0) {
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = protocol;
        addr.sin_addr.s_addr = htonl(INADDR_ANY);
        addr.sin_port = htons(listen_port);

        if (bind(sockfd, (sockaddr*)&addr, sizeof(addr)) == -1) {
            std::cerr << "Failed to bind to port " << listen_port 
                      << ": " << strerror(errno) << std::endl;
            close(sockfd);
            return -1;
        }
    }

    return sockfd;
}

// 解析命令行参数
bool parse_args(int argc, char* argv[], std::string& proxy_type,
                std::string& proxy_host, int& proxy_port,
                std::string& target_host, int& target_port,
                int& buffer_size, int& protocol, bool& show_debug) {
    // 解析命令行参数
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-x") == 0 && i + 1 < argc) {
            // 解析代理参数
            std::string proxy_str = argv[i + 1];
            std::string protocol;
            std::string host;
            int port;

            // 解析代理地址和端口
            if (sscanf(proxy_str.c_str(), "%[^:]://%[^:]:%d", &protocol, &host, &port) != 3) {
                std::cerr << "Invalid proxy parameter: " << proxy_str << std::endl;
                return false;
            }

            proxy_type = protocol;
            proxy_host = host;
            proxy_port = port;
            i++;

        } else if (strcmp(argv[i], "-6") == 0) {
            // 设置 IPv6 协议
            protocol = AF_INET6;

        } else if (strcmp(argv[i], "-4") == 0) {
            // 设置 IPv4 协议
            protocol = AF_INET;

        } else if (strcmp(argv[i], "-s") == 0 && i + 1 < argc) {
            // 设置缓冲区大小
            buffer_size = atoi(argv[i + 1]);
            i++;

        } else if (strcmp(argv[i], "-d") == 0) {
            // 显示调试信息
            show_debug = true;

        } else if (i + 1 < argc) {
            // 解析目标主机和端口
            target_host = argv[i];
            target_port = atoi(argv[i + 1]);
            i++;
        }
    }

    return true;
}

// 解析 IP 地址
bool parse_ip(const std::string& ip_str, struct in_addr* addr) {
    return inet_pton(AF_INET, ip_str.c_str(), addr) == 1;
}

bool parse_ipv6(const std::string& ip_str, struct in6_addr* addr) {
    return inet_pton(AF_INET6, ip_str.c_str(), addr) == 1;
}

// 检查代理连接
bool check_proxy_connection(const std::string& proxy_type,
                            const std::string& proxy_host, int proxy_port) {
    // TODO: 使用 `socks` 库检查代理连接
    // ...

    return true; // 假设代理连接正常
}

int main(int argc, char* argv[]) {
    std::string proxy_type;
    std::string proxy_host;
    int proxy_port;
    std::string target_host;
    int target_port;
    int buffer_size = BUFFER_SIZE;
    int protocol = AF_INET; // 默认 IPv4
    bool show_debug = false;

    // 解析命令行参数
    if (!parse_args(argc, argv, proxy_type, proxy_host, proxy_port,
                    target_host, target_port, buffer_size, protocol, show_debug)) {
        return 1;
    }

    // 检查代理连接
    if (proxy_type != "" && !check_proxy_connection(proxy_type, proxy_host, proxy_port)) {
        std::cerr << "Proxy connection check failed. Exiting." << std::endl;
        return 1;
    }

    // 解析目标主机名
    struct addrinfo hints;
    struct addrinfo* result;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = protocol;
    hints.ai_socktype = SOCK_DGRAM;

    if (getaddrinfo(target_host.c_str(), NULL, &hints, &result) != 0) {
        std::cerr << "Failed to resolve target host: " << target_host << std::endl;
        return 1;
    }

    // 打印解析后的 IP 地址
    struct in_addr addr;
    struct in6_addr addr6;

    for (struct addrinfo* p = result; p != NULL; p = p->ai_next) {
        if (p->ai_family == AF_INET && parse_ip(inet_ntoa(((sockaddr_in*)(p->ai_addr))->sin_addr), &addr)) {
            std::cout << "Resolved IPv4 address: " << inet_ntoa(addr) << std::endl;
        } else if (p->ai_family == AF_INET6 && parse_ipv6(inet_ntop(AF_INET6, &((sockaddr_in6*)(p->ai_addr))->sin6_addr, NULL, INET6_ADDRSTRLEN), &addr6)) {
            std::cout << "Resolved IPv6 address: " << inet_ntop(AF_INET6, &((sockaddr_in6*)(p->ai_addr))->sin6_addr, NULL, INET6_ADDRSTRLEN) << std::endl;
        }
    }

    freeaddrinfo(result);

    // 创建 UDP 套接字
    int sockfd = create_socket_and_bind(protocol, proxy_type, proxy_host, 
                                        proxy_port, 0, show_debug);
    if (sockfd == -1) {
        return 1;
    }

    // 发送 UDP 数据包
    // TODO: 使用 `socks` 库发送 UDP 数据包
    // ...

    // 接收 UDP 数据包
    // TODO: 使用 `socks` 库接收 UDP 数据包
    // ...

    // 关闭套接字
    close(sockfd);

    return 0;
}