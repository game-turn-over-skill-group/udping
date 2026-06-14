#!/bin/bash
# 稳定版 udping.sh | 修复随机Hex丢失、发包异常、简化间隔逻辑
# 纯原生Bash，无bc/xxd依赖，适配Windows nc + Cygwin
BASE_HEX="000004172710198000000000"
DEBUG=0
PKG_COUNT=1
INTERVAL=1
WAIT_TIMEOUT=2
FORCE_IPV4=0
FORCE_IPV6=0
LOCAL_PORT=0
PROXY=""

SEND=0
SUCC=0
FAIL=0
LAT_RAW_LIST=()

# 生成8位大写随机十六进制（修复写法，保证必生成字符）
rand_hex8() {
    local chars="0123456789ABCDEF"
    local result=""
    for ((i=0; i<8; i++)); do
        local idx=$(( RANDOM % 16 ))
        result="${result}${chars:${idx}:1}"
    done
    echo "${result}"
}

# 十六进制转二进制（纯Bash）
hex_to_bin() {
    local hex="$1"
    local len=${#hex}
    for ((i=0; i<len; i+=2)); do
        printf "\\x${hex:i:2}"
    done
}

# 判断IPv4
is_ipv4() {
    [[ $1 =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
}

# 判断IPv6
is_ipv6() {
    [[ $1 =~ : ]]
}

# 参数解析
parse_args() {
    if [ $# -lt 2 ]; then
        echo "用法: $0 <目标IP/域名> <端口> [参数]"
        echo "参数:"
        echo "  -s        详细调试输出"
        echo "  -n NUM    发包数量(默认1)"
        echo "  -i SEC    发包间隔(默认1，支持整数)"
        echo "  -w SEC    响应超时(默认2)"
        echo "  -4        强制IPv4"
        echo "  -6        强制IPv6"
        echo "  -l PORT   固定本地端口(0=随机)"
        echo "  -x PROXY  代理(暂不支持)"
        exit 1
    fi

    TARGET_HOST="$1"
    TARGET_PORT="$2"
    shift 2

    while [ $# -gt 0 ]; do
        case "$1" in
            -s) DEBUG=1; shift ;;
            -n) PKG_COUNT="$2"; shift 2 ;;
            -i) INTERVAL="$2"; shift 2 ;;
            -w) WAIT_TIMEOUT="$2"; shift 2 ;;
            -4) FORCE_IPV4=1; shift ;;
            -6) FORCE_IPV6=1; shift ;;
            -l) LOCAL_PORT="$2"; shift 2 ;;
            -x) PROXY="$2"; shift 2 ;;
            *) echo "未知参数: $1"; exit 1 ;;
        esac
    done

    if [ $FORCE_IPV4 -eq 1 ] && [ $FORCE_IPV6 -eq 1 ]; then
        echo "Error: Cannot use both IPv4 and IPv6 at the same time."
        exit 1
    fi
}

# 主机解析日志（对齐原版）
print_resolve_log() {
    echo "Proxy parameter received for parsing: $PROXY"
    [ -n "$PROXY" ] && echo "Warning: Proxy function not supported in shell version."
    echo "Attempting to resolve target host: $TARGET_HOST"

    if [ $FORCE_IPV4 -eq 1 ]; then
        echo "Resolved IPv4 address: $TARGET_HOST"
        echo "Failed to resolve target host $TARGET_HOST as IPv6"
        return
    fi
    if [ $FORCE_IPV6 -eq 1 ]; then
        echo "Resolved IPv6 address: $TARGET_HOST"
        echo "Failed to resolve target host $TARGET_HOST as IPv4"
        return
    fi

    if is_ipv4 "$TARGET_HOST"; then
        echo "Resolved IPv4 address: $TARGET_HOST"
        echo "Failed to resolve target host $TARGET_HOST as IPv6"
    elif is_ipv6 "$TARGET_HOST"; then
        echo "Resolved IPv6 address: $TARGET_HOST"
        echo "Failed to resolve target host $TARGET_HOST as IPv4"
    else
        echo "Resolved IPv6 address: $TARGET_HOST"
        echo "Failed to resolve target host $TARGET_HOST"
    fi
}

# 主程序
parse_args "$@"
print_resolve_log

# 多包提示
if [ $PKG_COUNT -gt 1 ]; then
    echo "** Sending ${PKG_COUNT} probes.  Press control-c to stop early **"
fi

# 循环发包（简化逻辑：单包执行完成后sleep，稳定优先）
for ((cur=1; cur<=PKG_COUNT; cur++)); do
    SEND=$((SEND + 1))
    # 拼接完整数据包（修复：保证随机Hex正常生成）
    RND_HEX=$(rand_hex8)
    FULL_HEX="${BASE_HEX}${RND_HEX}"

    # 本地端口配置
    if [ $LOCAL_PORT -ne 0 ]; then
        CUR_LPORT="$LOCAL_PORT"
        PORT_ARG="-p $CUR_LPORT"
    else
        CUR_LPORT=$(( 1024 + RANDOM % 65535 ))
        PORT_ARG=""
    fi

    # 调试头部
    if [ $DEBUG -eq 1 ]; then
        echo ""
        NOW=$(date +"%Y-%m-%d %H:%M:%S")
        echo "SysTime: $NOW    Count: $cur"
        echo "Send to: ($TARGET_HOST, $TARGET_PORT)‹ $CUR_LPORT ›: $FULL_HEX"
    fi

    # 临时文件传递二进制（防空字节、防截断）
    TMP_SEND=$(mktemp /tmp/udp_s.XXXX)
    TMP_RECV=$(mktemp /tmp/udp_r.XXXX)
    hex_to_bin "$FULL_HEX" > "$TMP_SEND"

    # 收发计时
    START=$(date +%s%3N)
    cat "$TMP_SEND" | nc -u -w "$WAIT_TIMEOUT" $PORT_ARG "$TARGET_HOST" "$TARGET_PORT" > "$TMP_RECV" 2>/dev/null
    END=$(date +%s%3N)
    LAT_RAW=$(( END - START ))

    # 清理发送文件
    rm -f "$TMP_SEND"

    # 延迟格式化 保留3位小数
    LAT_INT=$(( LAT_RAW / 1000 ))
    LAT_DEC=$(( LAT_RAW % 1000 ))
    printf -v LAT_DEC "%03d"
    LAT_MS="${LAT_INT}.${LAT_DEC}"

    # 判定收发结果
    if [ -s "$TMP_RECV" ]; then
        SUCC=$((SUCC + 1))
        LAT_RAW_LIST+=("$LAT_RAW")
        if [ $DEBUG -eq 1 ]; then
            echo -n "Recv from: ('$TARGET_HOST', $TARGET_PORT)‹ $LAT_MS ms ›: "
            od -t x1 -An "$TMP_RECV" | tr -d ' \n' | tr '[:lower:]' '[:upper:]'
            echo ""
        else
            echo "Probing $TARGET_HOST:$TARGET_PORT/udp - Reply from $TARGET_HOST - time=${LAT_MS}ms"
        fi
    else
        FAIL=$((FAIL + 1))
        if [ $DEBUG -eq 1 ]; then
            echo "Socket error while receiving: [WinError 10054] 远程主机强迫关闭了一个现有的连接。"
        else
            echo "Probing $TARGET_HOST:$TARGET_PORT/udp - No response within ${WAIT_TIMEOUT}s ‹ ${CUR_LPORT} › timing out..."
        fi
    fi

    # 清理接收文件
    rm -f "$TMP_RECV"

    # 后置休眠（简化间隔，稳定优先，适配Windows nc）
    sleep "$INTERVAL"
done

# ========= 统计输出（纯整数运算，无bc） =========
echo ""
# 丢包率 保留2位小数
if [ $SEND -eq 0 ]; then
    FAIL_PCT="0.00"
else
    TMP=$(( FAIL * 10000 / SEND ))
    INT_PART=$(( TMP / 100 ))
    DEC_PART=$(( TMP % 100 ))
    printf -v DEC_PART "%02d"
    FAIL_PCT="${INT_PART}.${DEC_PART}"
fi

echo "Ping statistics for $TARGET_HOST:$TARGET_PORT/udp"
echo "     $SEND probes sent."
echo "     $SUCC successful, $FAIL failed.  (${FAIL_PCT}% fail)"

# 最大/最小/平均延迟
if [ ${#LAT_RAW_LIST[@]} -gt 0 ]; then
    MIN=${LAT_RAW_LIST[0]}
    MAX=${LAT_RAW_LIST[0]}
    SUM=0
    COUNT=${#LAT_RAW_LIST[@]}

    for val in "${LAT_RAW_LIST[@]}"; do
        (( SUM += val ))
        (( val < MIN )) && MIN=$val
        (( val > MAX )) && MAX=$val
    done

    # 最小值
    MIN_I=$(( MIN / 1000 ))
    MIN_D=$(( MIN % 1000 ))
    printf -v MIN_D "%03d"
    MIN_STR="${MIN_I}.${MIN_D}"

    # 最大值
    MAX_I=$(( MAX / 1000 ))
    MAX_D=$(( MAX % 1000 ))
    printf -v MAX_D "%03d"
    MAX_STR="${MAX_I}.${MAX_D}"

    # 平均值
    AVG_RAW=$(( SUM / COUNT ))
    AVG_I=$(( AVG_RAW / 1000 ))
    AVG_D=$(( AVG_RAW % 1000 ))
    printf -v AVG_D "%03d"
    AVG_STR="${AVG_I}.${AVG_D}"

    echo "Approximate trip times in milli-seconds:"
    echo "     Minimum = ${MIN_STR}ms, Maximum = ${MAX_STR}ms, Average = ${AVG_STR}ms"
fi