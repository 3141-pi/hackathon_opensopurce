# -*- coding: utf-8 -*-
"""
MCP 服务器：查询“心狗家庭”成员列表（无参）
- 工具：list_family_members()
- 返回：我的家庭中一共有XX人，他们分别是XX
依赖：pip install mcp requests
"""

import logging
import sys
from typing import Any, Dict, List
from urllib.parse import quote

import requests
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("family_members_mcp")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

FAMILY_NAME = "心狗家庭"
FAMILY_LIST_URL = (
    "获取地址可联系1823492106@qq.com"
    + quote(FAMILY_NAME, safe="")
)
HTTP_TIMEOUT = 10  # 秒

mcp = FastMCP("family-members-list")


def _extract_names(data: Any) -> List[str]:
    """
    从接口返回 JSON 中抽取人名字段（索引 1 位置），并去重保序
    返回示例：[]
    """
    names: List[str] = []

    if isinstance(data, dict):
        iterable = data.values()
    elif isinstance(data, list):
        iterable = data
    else:
        logger.error("成员列表接口返回结构非预期（既不是 dict 也不是 list）")
        return names

    for row in iterable:
        try:
            if isinstance(row, (list, tuple)) and len(row) > 1 and row[1]:
                name_str = str(row[1]).strip()
                if name_str:
                    names.append(name_str)
        except Exception as e:
            logger.warning(f"解析成员行出错：{e}")

    # 去重保序
    seen = set()
    uniq: List[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


@mcp.tool()
async def list_family_members() -> str:
    """
    查询“心狗家庭”的所有成员姓名，不需要输入参数。
    返回：
      我的家庭中一共有XX人，他们分别是XX
    """
    try:
        resp = requests.get(FAMILY_LIST_URL, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        names = _extract_names(data)

        if not names:
            return "我的家庭中一共有0人，他们分别是"

        return f"我的家庭中一共有{len(names)}人，他们分别是{'、'.join(names)}"

    except requests.RequestException as e:
        logger.error(f"获取家庭成员网络错误：{e}")
        return f"获取家庭成员失败：网络错误（{str(e)}）"
    except Exception as e:
        logger.exception(f"获取或解析家庭成员失败：{e}")
        return f"获取家庭成员失败：{str(e)}"


if __name__ == "__main__":
    try:
        logger.info("启动家庭成员查询 MCP 服务器（无参）...")
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("服务器已退出（Ctrl+C）")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"服务器启动失败：{e}")
        sys.exit(1)
