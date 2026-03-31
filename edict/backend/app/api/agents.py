"""Agents API — Agent 配置和状态查询。"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

log = logging.getLogger("edict.api.agents")
router = APIRouter()

# Agent 元信息（对应 agents/ 目录下的 SOUL.md）
AGENT_META = {
    "stella": {"name": "星愿团长（Stella）", "role": "冒险团团长", "icon": "🌟"},
    "lyra": {"name": "莉雅（Lyra）", "role": "吟游诗人", "icon": "🎵"},
    "aria": {"name": "艾瑞娅（Aria）", "role": "元素法师", "icon": "🔮"},
    "sylvia": {"name": "希尔维亚（Sylvia）", "role": "森林游侠", "icon": "🌿"},
    "nina": {"name": "妮娜（Nina）", "role": "炼金术士", "icon": "⚗️"},
    "luna": {"name": "露娜（Luna）", "role": "月之祭司", "icon": "💫"},
    "kiana": {"name": "琪亚娜（Kiana）", "role": "女武神", "icon": "⚔️"},
    "mio": {"name": "美绪（Mio）", "role": "侦察兵", "icon": "🔍"},
    "hana": {"name": "花（Hana）", "role": "治疗师", "icon": "🌸"},
    "yui": {"name": "结衣（Yui）", "role": "机械师", "icon": "🤖"},
    "neko": {"name": "奈子（Neko）", "role": "猫耳斥候", "icon": "🐱"},
}


@router.get("")
async def list_agents():
    """列出所有可用 Agent。"""
    agents = []
    for agent_id, meta in AGENT_META.items():
        agents.append({
            "id": agent_id,
            **meta,
        })
    return {"agents": agents}


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """获取 Agent 详情。"""
    meta = AGENT_META.get(agent_id)
    if not meta:
        return {"error": f"Agent '{agent_id}' not found"}, 404

    # 尝试读取 SOUL.md
    soul_path = Path(__file__).parents[4] / "agents" / agent_id / "SOUL.md"
    soul_content = ""
    if soul_path.exists():
        soul_content = soul_path.read_text(encoding="utf-8")[:2000]

    return {
        "id": agent_id,
        **meta,
        "soul_preview": soul_content,
    }


@router.get("/{agent_id}/config")
async def get_agent_config(agent_id: str):
    """获取 Agent 运行时配置。"""
    config_path = Path(__file__).parents[4] / "data" / "agent_config.json"
    if not config_path.exists():
        return {"agent_id": agent_id, "config": {}}

    try:
        configs = json.loads(config_path.read_text(encoding="utf-8"))
        agent_config = configs.get(agent_id, {})
        return {"agent_id": agent_id, "config": agent_config}
    except (json.JSONDecodeError, IOError):
        return {"agent_id": agent_id, "config": {}}
