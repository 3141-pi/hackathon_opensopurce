# -*- coding: utf-8 -*-
"""
MCP 服务器：家庭成员校验后再进行历史健康数据检索
- 工具：analyze_health_data(user_name: str, user_query: str)
- 流程：
  1) 访问“心狗家庭”成员列表接口，提取所有成员姓名与 uid
  2) 将姓名统一转为小写拼音，与入参 user_name（小写拼音）匹配
  3) 若匹配成功，取该成员 uid，调用本地检索服务 http://127.0.0.1:8003/query 获取历史健康数据
  4) 若未匹配成功，返回“您不是我们的家庭成员，请找户主注册。”
依赖：pip install mcp requests pypinyin
"""

from mcp.server.fastmcp import FastMCP  # 导入FastMCP框架用于创建工具服务器
import logging  # 日志记录模块
import requests  # HTTP请求库
from urllib.parse import quote
from typing import Any, Dict, List
import re
from pypinyin import lazy_pinyin

# 创建日志记录器实例
logger = logging.getLogger('health_data_analyzer')

# 创建MCP服务器实例，命名为"Health Data Analyzer"
mcp = FastMCP("Health Data Analyzer")

# ----------------------------
# 家庭成员接口配置
# ----------------------------
FAMILY_NAME = "心狗家庭"
FAMILY_LIST_URL = (
    "获取地址可联系1823492106@qq.com"
    + quote(FAMILY_NAME, safe="")
)
HTTP_TIMEOUT = 10  # 秒


# ----------------------------
# 工具函数：姓名标准化 / 家庭成员拉取
# ----------------------------
def normalize_ascii_pinyin(s: str) -> str:
    """
    对已经是拉丁字符的名字进行清洗：去空格、只保留字母数字、转小写。
    """
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def name_to_lower_pinyin(name: str) -> str:
    """
    将中文姓名转小写拼音；若原本即为英文/拼音，则按 normalize 清洗。
    """
    if not name:
        return ""
    if all(ord(c) < 128 for c in name):
        return normalize_ascii_pinyin(name)
    # 含中文：转拼音再清洗
    py = "".join(lazy_pinyin(name))
    return normalize_ascii_pinyin(py)


def fetch_family_members() -> List[Dict[str, str]]:
    """
    读取家庭成员列表，返回结构：
    [
      { "uid": "23", "original_name": "刘成良", "pinyin": "liuchengliang" },
      ...
    ]
    """
    resp = requests.get(FAMILY_LIST_URL, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    members: List[Dict[str, str]] = []

    def _push(uid_val: Any, name_val: Any):
        if uid_val is None or name_val is None:
            return
        uid = str(uid_val).strip()
        original_name = str(name_val).strip()
        if not uid or not original_name:
            return
        pinyin_name = name_to_lower_pinyin(original_name)
        if not pinyin_name:
            return
        members.append(
            {
                "uid": uid,
                "original_name": original_name,
                "pinyin": pinyin_name,
            }
        )

    if isinstance(data, dict):
        for _, row in data.items():
            if isinstance(row, (list, tuple)) and len(row) > 1:
                _push(row[0], row[1])
    elif isinstance(data, list):
        for row in data:
            if isinstance(row, (list, tuple)) and len(row) > 1:
                _push(row[0], row[1])
    else:
        logger.error("家庭成员接口返回的结构非预期（既不是dict也不是list）")

    return members


# 使用装饰器注册工具函数，定义异步工具接口
@mcp.tool()
async def analyze_health_data(user_name: str, user_query: str) -> str:
    """当用户需要询问历史健康数据时比如体检数据或者其他文本信息或者用户的问题需要这些数据回答时调用该工具，先校验是否为“心狗家庭”成员，只有家庭成员才允许检索。

    参数:
        user_name: 用户名字的小写拼音（如 liuchengliang, tangxiaohan）
        user_query: 用户查询字符串（将传给本地检索服务）

    返回:
        - 若 user_name 属于“心狗家庭”：调用 http://127.0.0.1:8003/query 并格式化返回
        - 否则：返回“您不是我们的家庭成员，请找户主注册。”
    """

    # 入参基本校验与标准化
    if not isinstance(user_name, str) or not user_name.strip():
        return "请提供要查询的姓名（小写拼音），例如：liuchengliang、tangxiaohan。"

    query_name = normalize_ascii_pinyin(user_name)
    if not query_name:
        return "姓名格式不正确，请提供小写拼音（仅字母数字）。"

    try:
        # 1) 拉取家庭成员并匹配
        members = fetch_family_members()
        if not members:
            return "未获取到家庭成员名单，请稍后重试或联系户主。"

        # pinyin -> [members...]
        pinyin_index: Dict[str, List[Dict[str, str]]] = {}
        for m in members:
            pinyin_index.setdefault(m["pinyin"], []).append(m)

        candidates = pinyin_index.get(query_name, [])
        if not candidates:
            return "您不是我们的家庭成员，请找户主注册。"

        # 若存在同拼音重名，取第一位（可按需扩展歧义处理）
        target = candidates[0]
        uid = target["uid"]
        display_name = target["original_name"]

        logger.info(f"家庭成员匹配成功：{display_name} (UID: {uid}); 开始检索 user_query: {user_query}")

        # 2) 调用本地历史健康数据检索服务
        url = "获取地址可联系1823492106@qq.com"
        payload = {"uid": uid, "query": user_query}

        response = requests.post(url, json=payload, timeout=HTTP_TIMEOUT)

        if response.status_code == 200:
            result = response.json()

            # 兼容字段缺省
            rq_query = result.get("query", user_query)
            processing_time = result.get("processing_time", 0.0)
            top_results = result.get("top_results", [])

            analysis_result = f"""查询用户: {display_name} (UID: {uid})
查询问题: {rq_query}
处理时间: {processing_time:.4f}秒

相关健康数据分析结果：
{"=" * 50}
"""

            for i, hit in enumerate(top_results, 1):
                dept = hit.get("department", "")
                score = hit.get("score", 0.0)
                original_text = hit.get("original_text", "")
                summary_list = hit.get("summary", [])
                if isinstance(summary_list, list):
                    summary_text = "".join([f"  • {item}" for item in summary_list])
                else:
                    summary_text = f"  • {summary_list}"

                analysis_result += f"""
【匹配结果 {i}】
科室: {dept}
相似度: {score:.4f}
原文: {original_text}
总结:
{summary_text}
{"-" * 50}
"""

            logger.info(f"健康数据分析完成: {display_name} - {user_query}")
            return analysis_result.strip()

        else:
            error_msg = f"健康数据检索失败，HTTP状态码：{response.status_code}"
            logger.error(error_msg)
            return error_msg

    except requests.RequestException as e:
        # 处理网络连接错误
        error_msg = f"网络连接错误：{str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        # 处理其他未知错误
        error_msg = f"健康数据分析过程中发生未知错误：{str(e)}"
        logger.error(error_msg)
        return error_msg


# 启动服务器
if __name__ == "__main__":
    # 配置日志格式和级别
    logging.basicConfig(
        level=logging.INFO,  # 设置日志级别为INFO
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'  # 定义日志格式
    )

    # 启动MCP服务器，使用标准输入输出作为通信方式
    try:
        logger.info("启动支持家庭校验的健康数据分析 MCP 服务器...")
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("服务器已退出（Ctrl+C）")
    except Exception as e:
        logger.exception(f"启动服务器时出错: {e}")
