
### 源码使用方法：
```
python udp_tracker.py [-4 | -6] <domain> [<port>] [-s] [-t <wait_time_ms>]
python udping.py 域名 端口
python3 udping.py 域名 端口
```

### 例子：
```python
python udping.py ipv4.rer.lol 2710
python udping.py -4 btt.service.gongt.me 6969
python udping.py -6 btt.service.gongt.me 6969
python udping.py btt.service.gongt.me -s -t 500
```

### 其他参数说明：（加最后不能在前面）
```javascript
[-s] 显示当前系统时间打印
[-t] 持续探测 直到 CTRL+C 退出
[-t ms] 持续探测 精确到毫秒延迟 直到 CTRL+C 退出
```


### 友情提醒：
* 默认使用ipv4模式、如果域名包含ipv4+ipv6时, ipv4不工作又没自定义参数 则提示超时
* 使用-4/-6 自定义模式 可解决
* 延迟最好不要低于100ms(自己除外)否则可能被tracker限速/拉黑（推荐: 250~500 ms）


### 安装依赖：
```python
pip install pyinstaller
python.exe -m pip install --upgrade pip
```

### 编译方法：（cd进入py脚本目录）
```python
pyinstaller --onefile udping.py
```



##### 项目发起人：rer
##### 项目协作者：ChatGPT

