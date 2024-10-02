#include <iostream>
#include <thread>
#include <mutex>
#include <vector>
#include <string>
#include <algorithm>  // 引入该头文件以使用 std::all_of
#include <cctype>     // 引入该头文件以使用 std::isdigit
#include <random>
#include <chrono>
#include <cstring>
#include <stdexcept>
#include <cstdlib>
#include <csignal>
#include <arpa/inet.h>
#include <unistd.h>
#include <netdb.h>
#include <getopt.h>
#include <sys/socket.h>
#include <cerrno>

std::mutex lock;

// 随机生成+改动结尾部分数据包
std::string generate_default_hex_data() {
    const char hex_chars[] = "0123456789ABCDEF";
    std::string default_hex_data = "000004172710198000000000";
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 15);
    for (int i = 0; i < 8; ++i) {
        default_hex_data += hex_chars[dis(gen)];
    }
    return default_hex_data;
}

// 创建socket绑定
int create_socket_and_bind(int protocol, const std::string& proxy_type, const std::string& proxy_host, int proxy_port, int& listen_port, bool show_debug) {
    int client_socket;
    struct sockaddr_in6 addr6;
    struct sockaddr_in addr4;

    try {
        if (show_debug) {
            std::cout << "\ncreate_socket_and_bind: protocol: " << protocol 
                      << ", proxy_type: " << proxy_type 
                      << ", proxy_host: " << proxy_host 
                      << ", proxy_port: " << proxy_port 
                      << ", listen_port: " << listen_port << std::endl;
        }

        // 创建socket
        if (proxy_type == "socks") {
            // 这里只是示例，完整的SOCKS5代理需要专门的实现或库来支持
            if (show_debug) {
                std::cout << "Creating SOCKS5 Proxy socket..." << std::endl;
            }
            // SOCKS代理的完整实现需使用专门库
            std::cerr << "SOCKS5 proxy not implemented in this example." << std::endl;
            return -1;
        } else {
            if (show_debug) {
                std::cout << "Creating Direct Connection socket..." << std::endl;
            }
            client_socket = socket(protocol, SOCK_DGRAM, 0);
            if (client_socket < 0) {
                std::cerr << "Failed to create socket: " << strerror(errno) << std::endl;
                return -1;
            }
        }

        // 如果 listen_port 为 0，使用随机端口
        if (listen_port == 0) {
            std::random_device rd;
            std::mt19937 gen(rd());
            std::uniform_int_distribution<> dis(1024, 65535);
            listen_port = dis(gen);
        }

        // 绑定IPv6或IPv4
        if (protocol == AF_INET6) {
            if (show_debug) {
                std::cout << "Binding as IPv6..." << std::endl;
            }
            memset(&addr6, 0, sizeof(addr6));
            addr6.sin6_family = AF_INET6;
            addr6.sin6_addr = in6addr_any;
            addr6.sin6_port = htons(listen_port);

            if (bind(client_socket, (struct sockaddr*)&addr6, sizeof(addr6)) < 0) {
                std::cerr << "Failed to bind to port " << listen_port << ": " << strerror(errno) << std::endl;
                close(client_socket);
                return -1;
            }
        } else {
            if (show_debug) {
                std::cout << "Binding as IPv4..." << std::endl;
            }
            memset(&addr4, 0, sizeof(addr4));
            addr4.sin_family = AF_INET;
            addr4.sin_addr.s_addr = INADDR_ANY;
            addr4.sin_port = htons(listen_port);

            if (bind(client_socket, (struct sockaddr*)&addr4, sizeof(addr4)) < 0) {
                std::cerr << "Failed to bind to port " << listen_port << ": " << strerror(errno) << std::endl;
                close(client_socket);
                return -1;
            }
        }

        // 获取绑定的端口
        if (protocol == AF_INET6) {
            socklen_t len = sizeof(addr6);
            if (getsockname(client_socket, (struct sockaddr*)&addr6, &len) == 0) {
                listen_port = ntohs(addr6.sin6_port);
            }
        } else {
            socklen_t len = sizeof(addr4);
            if (getsockname(client_socket, (struct sockaddr*)&addr4, &len) == 0) {
                listen_port = ntohs(addr4.sin_port);
            }
        }

        if (show_debug) {
            std::cout << "Listening on port " << listen_port << "... ok" << std::endl;
        }
        return client_socket;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return -1;
    }
}

void clear_socket_buffer(int client, bool show_debug) {
    char buffer[4096];
    struct sockaddr_in addr;
    socklen_t addr_len = sizeof(addr);
    struct timeval timeout = {0, 10000}; // 0.01 seconds
    setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    while (true) {
        ssize_t len = recvfrom(client, buffer, sizeof(buffer), 0, (struct sockaddr*)&addr, &addr_len);
        if (len < 0) {
            if (errno == EWOULDBLOCK || errno == EAGAIN) {
                break;
            } else {
                if (show_debug) {
                    std::cerr << "Error while clearing socket buffer: " << strerror(errno) << std::endl;
                }
                break;
            }
        }
        if (show_debug) {
            std::cout << "Clearing socket buffer, discarded packet from: " << inet_ntoa(addr.sin_addr) << std::endl;
        }
    }
    timeout.tv_sec = 0;
    timeout.tv_usec = 0;
    setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
}

void precise_sleep(double duration) {
    auto start = std::chrono::high_resolution_clock::now();
    while (std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - start).count() < duration) {
        // Busy-wait loop
    }
}

void udp_tracker(const std::string& target_host, int target_port, const std::vector<std::string>& hex_data_packets, int listen_port, bool use_ipv4, bool use_ipv6, bool show_debug, bool continuous, double interval_time, double wait_time) {
    int protocol = use_ipv6 ? AF_INET6 : AF_INET;
    struct addrinfo hints = {}, *res;
    hints.ai_family = protocol;
    hints.ai_socktype = SOCK_DGRAM;
    if (getaddrinfo(target_host.c_str(), nullptr, &hints, &res) != 0) {
        std::cerr << "Failed to resolve target host " << target_host << std::endl;
        return;
    }

    int client = socket(protocol, SOCK_DGRAM, 0);
    if (client < 0) {
        std::cerr << "Failed to create socket: " << strerror(errno) << std::endl;
        return;
    }

    struct sockaddr_in6 addr6 = {};
    struct sockaddr_in addr4 = {};
    if (protocol == AF_INET6) {
        addr6.sin6_family = AF_INET6;
        addr6.sin6_port = htons(listen_port);
        addr6.sin6_addr = in6addr_any;
        if (bind(client, (struct sockaddr*)&addr6, sizeof(addr6)) < 0) {
            std::cerr << "Failed to bind to port " << listen_port << ": " << strerror(errno) << std::endl;
            close(client);
            return;
        }
    } else {
        addr4.sin_family = AF_INET;
        addr4.sin_port = htons(listen_port);
        addr4.sin_addr.s_addr = INADDR_ANY;
        if (bind(client, (struct sockaddr*)&addr4, sizeof(addr4)) < 0) {
            std::cerr << "Failed to bind to port " << listen_port << ": " << strerror(errno) << std::endl;
            close(client);
            return;
        }
    }

    int count = 0;
    int sent_packets = 0;
    try {
        if (continuous) {
            while (true) {
                for (const auto& hex_data : hex_data_packets) {
                    count++;
                    sent_packets++;
                    std::vector<uint8_t> data(hex_data.size() / 2);
                    for (size_t i = 0; i < hex_data.size(); i += 2) {
                        try {
                            std::string byte_str = hex_data.substr(i, 2);
                            data[i / 2] = std::stoi(byte_str, nullptr, 16);  // 将十六进制转换为整数
                        } catch (const std::invalid_argument& e) {
                            std::cerr << "Error: Invalid hex data '" << hex_data.substr(i, 2) << "' at position " << i << std::endl;
                            return;
                        } catch (const std::out_of_range& e) {
                            std::cerr << "Error: Hex data out of range at position " << i << std::endl;
                            return;
                        }
                    }

                    for (size_t i = 0; i < hex_data.size(); i += 2) {
                        data[i / 2] = std::stoi(hex_data.substr(i, 2), nullptr, 16);
                    }

                    if (data.size() > 18) {
                        std::cerr << "Warning: Data packet length " << data.size() << " exceeds buffer size 18. Truncating..." << std::endl;
                        data.resize(18);
                    }

                    {
                        std::lock_guard<std::mutex> guard(lock);
                        if (show_debug) {
                            std::cout << "Send to: (" << target_host << ", " << target_port << "): " << hex_data << std::endl;
                        }
                        clear_socket_buffer(client, show_debug);
                        sendto(client, data.data(), data.size(), 0, res->ai_addr, res->ai_addrlen);

                        auto start_time = std::chrono::high_resolution_clock::now();
                        char buffer[4096];
                        struct sockaddr_storage from;
                        socklen_t from_len = sizeof(from);
                        struct timeval timeout = {static_cast<int>(wait_time), static_cast<int>((wait_time - static_cast<int>(wait_time)) * 1000000)};
                        setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
                        ssize_t len = recvfrom(client, buffer, sizeof(buffer), 0, (struct sockaddr*)&from, &from_len);
                        auto end_time = std::chrono::high_resolution_clock::now();
                        if (len > 0) {
                            double response_time = std::chrono::duration<double, std::milli>(end_time - start_time).count();
                            if (show_debug) {
                                std::cout << "Recv from: " << inet_ntoa(((struct sockaddr_in*)&from)->sin_addr) << ": " << std::string(buffer, len) << " (" << response_time << " ms)" << std::endl;
                            } else {
                                std::cout << "Recv from: " << inet_ntoa(((struct sockaddr_in*)&from)->sin_addr) << " (" << response_time << " ms)" << std::endl;
                            }
                        } else if (errno == EWOULDBLOCK || errno == EAGAIN) {
                            std::cout << "No response within " << wait_time << " seconds, timing out..." << std::endl;
                        } else {
                            std::cerr << "Socket error while receiving: " << strerror(errno) << std::endl;
                        }
                    }

                    precise_sleep(interval_time);
                }
            }
        } else {
            for (const auto& hex_data : hex_data_packets) {
                count++;
                sent_packets++;
                std::vector<uint8_t> data(hex_data.size() / 2);
                for (size_t i = 0; i < hex_data.size(); i += 2) {
                    try {
                        std::string byte_str = hex_data.substr(i, 2);
                        data[i / 2] = std::stoi(byte_str, nullptr, 16);  // 将十六进制转换为整数
                    } catch (const std::invalid_argument& e) {
                        std::cerr << "Error: Invalid hex data '" << hex_data.substr(i, 2) << "' at position " << i << std::endl;
                        return;
                    } catch (const std::out_of_range& e) {
                        std::cerr << "Error: Hex data out of range at position " << i << std::endl;
                        return;
                    }
                }

                if (show_debug) {
                    std::cout << "Send to: (" << target_host << ", " << target_port << "): " << hex_data << std::endl;
                }
                clear_socket_buffer(client, show_debug);
                sendto(client, data.data(), data.size(), 0, res->ai_addr, res->ai_addrlen);

                auto start_time = std::chrono::high_resolution_clock::now();
                char buffer[4096];
                struct sockaddr_storage from;
                socklen_t from_len = sizeof(from);
                struct timeval timeout = {static_cast<int>(wait_time), static_cast<int>((wait_time - static_cast<int>(wait_time)) * 1000000)};
                setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
                ssize_t len = recvfrom(client, buffer, sizeof(buffer), 0, (struct sockaddr*)&from, &from_len);
                auto end_time = std::chrono::high_resolution_clock::now();
                if (len > 0) {
                    double response_time = std::chrono::duration<double, std::milli>(end_time - start_time).count();
                    if (show_debug) {
                        std::cout << "Recv from: " << inet_ntoa(((struct sockaddr_in*)&from)->sin_addr) << ": " << std::string(buffer, len) << " (" << response_time << " ms)" << std::endl;
                    } else {
                        std::cout << "Recv from: " << inet_ntoa(((struct sockaddr_in*)&from)->sin_addr) << " (" << response_time << " ms)" << std::endl;
                    }
                } else if (errno == EWOULDBLOCK || errno == EAGAIN) {
                    std::cout << "No response within " << wait_time << " seconds, timing out..." << std::endl;
                } else {
                    std::cerr << "Socket error while receiving: " << strerror(errno) << std::endl;
                }

                precise_sleep(interval_time);
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Unexpected error: " << e.what() << std::endl;
    }

    close(client);
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <target_host> [target_port] [hex_data_packets...]" << std::endl;
        return 1;
    }

    std::string target_host = argv[1];  // 第一个参数是目标主机
    int target_port = 6969;  // 默认端口

    // 声明 hex_data_packets
    std::vector<std::string> hex_data_packets;

    // 检查第二个参数是否是有效的端口号
    if (argc > 2) {
        // 判断第二个参数是否为空或以'-'符号开头
        if (argv[2][0] == '\0' || argv[2][0] == '-') {
            target_port = 6969;  // 使用默认端口
        } else if (std::all_of(argv[2], argv[2] + strlen(argv[2]), ::isdigit)) {
            target_port = std::stoi(argv[2]);  // 如果是数字，使用该数字作为端口号
        } else {
            std::cerr << "Error: Invalid port number provided: " << argv[2] << std::endl;
            target_port = 6969;  // 如果不是数字，使用默认端口
        }
    } else {
        target_port = 6969;  // 如果没有提供第二个参数，使用默认端口
    }
    // 检查第三个参数是否提供了数据包，如果没有或是选项，则使用默认数据包
    if (argc <= 3 || argv[3][0] == '-') {
        hex_data_packets.push_back(generate_default_hex_data()); //使用默认数据包
    } else {
        // 处理 hex_data_packets 参数
        for (int i = 3; i < argc; ++i) {
            if (argv[i][0] != '-') {  // 确保不是命令行参数
                // 检查是否为有效的十六进制字符串
                if (std::all_of(argv[i], argv[i] + strlen(argv[i]), [](char c) {
                        return std::isxdigit(c);
                    })) {
                    hex_data_packets.push_back(argv[i]); //使用自定义数据包
                } else {
                    std::cerr << "Error: Invalid hex data packet provided: " << argv[i] << std::endl;
                }
            }
        }
    }

    // 其余选项处理
    int listen_port = 0;
    bool use_ipv4 = false;
    bool use_ipv6 = false;
    bool show_debug = true;
    bool continuous = false;
    double interval_time = 1.0;
    double wait_time = 2.0;

    int opt;
    while ((opt = getopt(argc, argv, "46sl:c:i:w:")) != -1) {
        switch (opt) {
            case '4':
                use_ipv4 = true;
                break;
            case '6':
                use_ipv6 = true;
                break;
            case 's':
                show_debug = true;
                break;
            case 'l':
                listen_port = std::stoi(optarg);
                break;
            case 'c':
                continuous = true;
                break;
            case 'i':
                interval_time = std::stod(optarg);
                break;
            case 'w':
                wait_time = std::stod(optarg);
                break;
            default:
                std::cerr << "Usage: " << argv[0] << " <target_host> [target_port] [hex_data_packets...] [-4] [-6] [-s] [-l listen_port] [-c] [-i interval_time] [-w wait_time]" << std::endl;
                return 1;
        }
    }

    // 确保不会同时使用 IPv4 和 IPv6
    if (use_ipv4 && use_ipv6) {
        std::cerr << "Error: Cannot use both IPv4 and IPv6 at the same time." << std::endl;
        return 1;
    }

    // 调试输出
    if (show_debug) {
        std::cout << "Target host: " << target_host << ", Target port: " << target_port << std::endl;
        std::cout << "Packets to send: " << hex_data_packets.size() << std::endl;
    }

    // 开始 UDP Tracker 任务
    udp_tracker(target_host, target_port, hex_data_packets, listen_port, use_ipv4, use_ipv6, show_debug, continuous, interval_time, wait_time);

    return 0;
}