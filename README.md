这是个基于心狗云平台的mcp诊断工具，需要心狗云平台的api链接，如果需要请联系1823492106@qq.com
运行方式
环境准备：pip install python-dotenv>=1.0.0
websockets>=11.0.3 
mcp>=1.8.1
pydantic>=2.11.4
cd 文件夹路径
设置环境变量
$env:MCP_ENDPOINT ="ws://202.120.48.10:8004/mcp_endpoint/mcp/?token=A407NXE9nLEoXIn1Zccf5Yiw96BqnX3V0kCkgSGnT4fT%2BxltUI4MjJNkXEn9C%2F2%2B"
（上述服务器路径属于私有不保证随时开放，建议自己搜索部署mcp中转服务的部署方式）
python mcp_pipe.py (运行你希望的文件即可)
