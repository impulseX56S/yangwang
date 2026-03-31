"""
朝堂议政引擎 — 多官员实时讨论系统

灵感来源于 nvwa 项目的 group_chat + crew_engine
将官员可视化 + 实时讨论 + 用户（皇帝）参与融合到三省六部

功能:
  - 选择官员参与议政
  - 围绕旨意/议题进行多轮群聊讨论
  - 皇帝可随时发言、下旨干预（天命降临）
  - 命运骰子：随机事件
  - 每个官员保持自己的角色性格和说话风格
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid

logger = logging.getLogger('court_discuss')

# ── 官员角色设定 ──

OFFICIAL_PROFILES = {
    'stella': {
        'name': '星愿团长', 'emoji': '🌟', 'role': '团长',
        'duty': '冒险团团长。负责领导团队，制定冒险目标，协调团队成员。',
        'personality': '勇敢、智慧、充满领导力，是团队的核心和精神支柱。',
        'speaking_style': '自信坚定，经常说"大家准备好了吗？让我们出发吧！"、"我会带领大家完成这次冒险的！"。'
    },
    'lyra': {
        'name': '莉雅', 'emoji': '🎵', 'role': '吟游诗人',
        'duty': '吟游诗人。负责记录冒险故事，鼓舞团队士气，提供精神支持。',
        'personality': '活泼、开朗、充满艺术气息，总是能给团队带来欢乐。',
        'speaking_style': '轻盈欢快，经常说"团长～听我为您唱首歌吧"、"这次冒险一定会成为传说的！"。'
    },
    'aria': {
        'name': '艾瑞娅', 'emoji': '🔮', 'role': '元素法师',
        'duty': '元素法师。负责使用魔法解决问题，提供远程攻击和支援。',
        'personality': '神秘、智慧、有点傲娇，对魔法有着深厚的造诣。',
        'speaking_style': '优雅神秘，经常说"团长～看我的魔法！"、"这点小事交给我来处理吧"。'
    },
    'sylvia': {
        'name': '希尔维亚', 'emoji': '🌿', 'role': '森林游侠',
        'duty': '森林游侠。负责侦察、追踪和远程攻击，熟悉野外生存。',
        'personality': '冷静、敏锐、善于观察，是团队的眼睛和耳朵。',
        'speaking_style': '冷静从容，经常说"团长，前方发现情况"、"我来为大家开路"。'
    },
    'nina': {
        'name': '妮娜', 'emoji': '⚗️', 'role': '炼金术士',
        'duty': '炼金术士。负责制作药水、道具和装备，提供后勤支持。',
        'personality': '好奇、聪明、有点疯狂，对炼金术有着无限的热情。',
        'speaking_style': '兴奋好奇，经常说"团长～看我新发明的药水！"、"这个配方一定会成功的！"。'
    },
    'luna': {
        'name': '露娜', 'emoji': '💫', 'role': '月之祭司',
        'duty': '月之祭司。负责治疗、祝福和占卜，提供精神和生命支持。',
        'personality': '温柔、善良、充满神圣感，总是能给团队带来希望。',
        'speaking_style': '温柔神圣，经常说"团长～让我为您祝福"、"愿月光指引我们的道路"。'
    },
    'kiana': {
        'name': '琪亚娜', 'emoji': '⚔️', 'role': '女武神',
        'duty': '女武神。负责近战攻击和保护团队，是团队的盾牌和利刃。',
        'personality': '勇敢、坚强、有点傲娇，总是冲在战斗的最前线。',
        'speaking_style': '坚定有力，经常说"团长～让我来保护您！"、"敌人交给我来对付！"。'
    },
    'mio': {
        'name': '美绪', 'emoji': '🔍', 'role': '侦察兵',
        'duty': '侦察兵。负责侦察、情报收集和陷阱布置，确保团队安全。',
        'personality': '细心、敏捷、有点调皮，总是能发现别人忽略的细节。',
        'speaking_style': '活泼灵动，经常说"团长～我发现了一条秘密通道！"、"小心，前面有陷阱！"。'
    },
    'hana': {
        'name': '花', 'emoji': '🌸', 'role': '治疗师',
        'duty': '治疗师。负责治疗伤病，提供生命恢复和状态增益。',
        'personality': '温柔、善良、充满爱心，总是关心团队成员的健康。',
        'speaking_style': '温柔体贴，经常说"团长～让我为您疗伤"、"大家都要平平安安的哦"。'
    },
    'yui': {
        'name': '结衣', 'emoji': '🤖', 'role': '机械师',
        'duty': '机械师。负责制造和维修机械装置，提供技术支持。',
        'personality': '聪明、理性、有点机器人般的思维，对机械有着深厚的了解。',
        'speaking_style': '理性冷静，经常说"团长～机械装置已修复"、"数据分析完毕，建议采取以下行动"。'
    },
    'neko': {
        'name': '奈子', 'emoji': '🐱', 'role': '猫耳斥候',
        'duty': '猫耳斥候。负责侦察、潜行和情报收集，行动敏捷。',
        'personality': '活泼、调皮、有点任性，总是充满活力。',
        'speaking_style': '可爱调皮，经常说"团长～喵～发现敌人了！"、"人家的耳朵可是很灵的哦♡"。'
    },
}

# ── 命运骰子事件（古风版）──

FATE_EVENTS = [
    '八百里加急：边疆战报传来，所有人必须讨论应急方案',
    '钦天监急报：天象异常，太史公占卜后建议暂缓此事',
    '新科状元觐见，带来了意想不到的新视角',
    '匿名奏折揭露了计划中一个被忽视的重大漏洞',
    '户部清点发现国库余银比预期多一倍，可以加大投入',
    '一位告老还乡的前朝元老突然上书，分享前车之鉴',
    '民间舆论突变，百姓对此事态度出现180度转折',
    '邻国使节来访，带来了合作机遇也带来了竞争压力',
    '太后懿旨：要求优先考虑民生影响',
    '暴雨连日，多地受灾，资源需重新调配',
    '发现前朝古籍中竟有类似问题的解决方案',
    '翰林院提出了一个大胆的替代方案，令人耳目一新',
    '各部积压的旧案突然需要一起处理，人手紧张',
    '皇帝做了一个意味深长的梦，暗示了一个全新的方向',
    '突然有人拿出了竞争对手的情报，局面瞬间改变',
    '一场意外让所有人不得不在半天内拿出结论',
]

# ── Session 管理 ──

_sessions: dict[str, dict] = {}


def create_session(topic: str, official_ids: list[str], task_id: str = '') -> dict:
    """创建新的朝堂议政会话。"""
    session_id = str(uuid.uuid4())[:8]

    officials = []
    for oid in official_ids:
        profile = OFFICIAL_PROFILES.get(oid)
        if profile:
            officials.append({**profile, 'id': oid})

    if not officials:
        return {'ok': False, 'error': '至少选择一位官员'}

    session = {
        'session_id': session_id,
        'topic': topic,
        'task_id': task_id,
        'officials': officials,
        'messages': [{
            'type': 'system',
            'content': f'🏛 朝堂议政开始 —— 议题：{topic}',
            'timestamp': time.time(),
        }],
        'round': 0,
        'phase': 'discussing',  # discussing | concluded
        'created_at': time.time(),
    }

    _sessions[session_id] = session
    return _serialize(session)


def advance_discussion(session_id: str, user_message: str = None,
                       decree: str = None) -> dict:
    """推进一轮讨论，使用内置模拟或 LLM。"""
    session = _sessions.get(session_id)
    if not session:
        return {'ok': False, 'error': f'会话 {session_id} 不存在'}

    session['round'] += 1
    round_num = session['round']

    # 记录皇帝发言
    if user_message:
        session['messages'].append({
            'type': 'emperor',
            'content': user_message,
            'timestamp': time.time(),
        })

    # 记录天命降临
    if decree:
        session['messages'].append({
            'type': 'decree',
            'content': decree,
            'timestamp': time.time(),
        })

    # 尝试用 LLM 生成讨论
    llm_result = _llm_discuss(session, user_message, decree)

    if llm_result:
        new_messages = llm_result.get('messages', [])
        scene_note = llm_result.get('scene_note')
    else:
        # 降级到规则模拟
        new_messages = _simulated_discuss(session, user_message, decree)
        scene_note = None

    # 添加到历史
    for msg in new_messages:
        session['messages'].append({
            'type': 'official',
            'official_id': msg.get('official_id', ''),
            'official_name': msg.get('name', ''),
            'content': msg.get('content', ''),
            'emotion': msg.get('emotion', 'neutral'),
            'action': msg.get('action'),
            'timestamp': time.time(),
        })

    if scene_note:
        session['messages'].append({
            'type': 'scene_note',
            'content': scene_note,
            'timestamp': time.time(),
        })

    return {
        'ok': True,
        'session_id': session_id,
        'round': round_num,
        'new_messages': new_messages,
        'scene_note': scene_note,
        'total_messages': len(session['messages']),
    }


def get_session(session_id: str) -> dict | None:
    session = _sessions.get(session_id)
    if not session:
        return None
    return _serialize(session)


def conclude_session(session_id: str) -> dict:
    """结束议政，生成总结。"""
    session = _sessions.get(session_id)
    if not session:
        return {'ok': False, 'error': f'会话 {session_id} 不存在'}

    session['phase'] = 'concluded'

    # 尝试用 LLM 生成总结
    summary = _llm_summarize(session)
    if not summary:
        # 降级到简单统计
        official_msgs = [m for m in session['messages'] if m['type'] == 'official']
        by_name = {}
        for m in official_msgs:
            name = m.get('official_name', '?')
            by_name[name] = by_name.get(name, 0) + 1
        parts = [f"{n}发言{c}次" for n, c in by_name.items()]
        summary = f"历经{session['round']}轮讨论，{'、'.join(parts)}。议题待后续落实。"

    session['messages'].append({
        'type': 'system',
        'content': f'📋 朝堂议政结束 —— {summary}',
        'timestamp': time.time(),
    })
    session['summary'] = summary

    return {
        'ok': True,
        'session_id': session_id,
        'summary': summary,
    }


def list_sessions() -> list[dict]:
    """列出所有活跃会话。"""
    return [
        {
            'session_id': s['session_id'],
            'topic': s['topic'],
            'round': s['round'],
            'phase': s['phase'],
            'official_count': len(s['officials']),
            'message_count': len(s['messages']),
        }
        for s in _sessions.values()
    ]


def destroy_session(session_id: str):
    _sessions.pop(session_id, None)


def get_fate_event() -> str:
    """获取随机命运骰子事件。"""
    import random
    return random.choice(FATE_EVENTS)


# ── LLM 集成 ──

_PREFERRED_MODELS = ['gpt-4o-mini', 'claude-haiku', 'gpt-5-mini', 'gemini-3-flash', 'gemini-flash']

# GitHub Copilot 模型列表 (通过 Copilot Chat API 可用)
_COPILOT_MODELS = [
    'gpt-4o', 'gpt-4o-mini', 'claude-sonnet-4', 'claude-haiku-3.5',
    'gemini-2.0-flash', 'o3-mini',
]
_COPILOT_PREFERRED = ['gpt-4o-mini', 'claude-haiku', 'gemini-flash', 'gpt-4o']


def _pick_chat_model(models: list[dict]) -> str | None:
    """从 provider 的模型列表中选一个适合聊天的轻量模型。"""
    ids = [m['id'] for m in models if isinstance(m, dict) and 'id' in m]
    for pref in _PREFERRED_MODELS:
        for mid in ids:
            if pref in mid:
                return mid
    return ids[0] if ids else None


def _read_copilot_token() -> str | None:
    """读取 openclaw 管理的 GitHub Copilot token。"""
    token_path = os.path.expanduser('~/.openclaw/credentials/github-copilot.token.json')
    if not os.path.exists(token_path):
        return None
    try:
        with open(token_path) as f:
            cred = json.load(f)
        token = cred.get('token', '')
        expires = cred.get('expiresAt', 0)
        # 检查 token 是否过期（毫秒时间戳）
        import time
        if expires and time.time() * 1000 > expires:
            logger.warning('Copilot token expired')
            return None
        return token if token else None
    except Exception as e:
        logger.warning('Failed to read copilot token: %s', e)
        return None


def _get_llm_config() -> dict | None:
    """从 openclaw 配置读取 LLM 设置，支持环境变量覆盖。

    优先级: 环境变量 > github-copilot token > 本地 copilot-proxy > anthropic > 其他 provider
    """
    # 1. 环境变量覆盖（保留向后兼容）
    env_key = os.environ.get('OPENCLAW_LLM_API_KEY', '')
    if env_key:
        return {
            'api_key': env_key,
            'base_url': os.environ.get('OPENCLAW_LLM_BASE_URL', 'https://api.openai.com/v1'),
            'model': os.environ.get('OPENCLAW_LLM_MODEL', 'gpt-4o-mini'),
            'api_type': 'openai',
        }

    # 2. GitHub Copilot token（最优先 — 免费、稳定、无需额外配置）
    copilot_token = _read_copilot_token()
    if copilot_token:
        # 选一个 copilot 支持的模型
        model = 'gpt-4o'
        logger.info('Court discuss using github-copilot token, model=%s', model)
        return {
            'api_key': copilot_token,
            'base_url': 'https://api.githubcopilot.com',
            'model': model,
            'api_type': 'github-copilot',
        }

    # 3. 从 ~/.openclaw/openclaw.json 读取其他 provider 配置
    openclaw_cfg = os.path.expanduser('~/.openclaw/openclaw.json')
    if not os.path.exists(openclaw_cfg):
        return None

    try:
        with open(openclaw_cfg) as f:
            cfg = json.load(f)

        providers = cfg.get('models', {}).get('providers', {})

        # 按优先级排序：copilot-proxy > anthropic > 其他
        ordered = []
        for preferred in ['copilot-proxy', 'anthropic']:
            if preferred in providers:
                ordered.append(preferred)
        ordered.extend(k for k in providers if k not in ordered)

        for name in ordered:
            prov = providers.get(name)
            if not prov:
                continue
            api_type = prov.get('api', '')
            base_url = prov.get('baseUrl', '')
            api_key = prov.get('apiKey', '')
            if not base_url:
                continue

            # 跳过无 key 且非本地的 provider
            if not api_key or api_key == 'n/a':
                if 'localhost' not in base_url and '127.0.0.1' not in base_url:
                    continue

            model_id = _pick_chat_model(prov.get('models', []))
            if not model_id:
                continue

            # 本地代理先探测是否可用
            if 'localhost' in base_url or '127.0.0.1' in base_url:
                try:
                    import urllib.request
                    probe = urllib.request.Request(base_url.rstrip('/') + '/models', method='GET')
                    urllib.request.urlopen(probe, timeout=2)
                except Exception:
                    logger.info('Skipping provider=%s (not reachable)', name)
                    continue

            logger.info('Court discuss using openclaw provider=%s model=%s api=%s', name, model_id, api_type)
            send_auth = prov.get('authHeader', True) is not False and api_key not in ('', 'n/a')
            return {
                'api_key': api_key if send_auth else '',
                'base_url': base_url,
                'model': model_id,
                'api_type': api_type,
            }
    except Exception as e:
        logger.warning('Failed to read openclaw config: %s', e)

    return None


def _llm_complete(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str | None:
    """调用 LLM API（自动适配 GitHub Copilot / OpenAI / Anthropic 协议）。"""
    config = _get_llm_config()
    if not config:
        return None

    import urllib.request
    import urllib.error

    api_type = config.get('api_type', 'openai-completions')

    if api_type == 'anthropic-messages':
        # Anthropic Messages API
        url = config['base_url'].rstrip('/') + '/v1/messages'
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': config['api_key'],
            'anthropic-version': '2023-06-01',
        }
        payload = json.dumps({
            'model': config['model'],
            'system': system_prompt,
            'messages': [{'role': 'user', 'content': user_prompt}],
            'max_tokens': max_tokens,
            'temperature': 0.9,
        }).encode()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data['content'][0]['text']
        except Exception as e:
            logger.warning('Anthropic LLM call failed: %s', e)
            return None
    else:
        # OpenAI-compatible API (也适用于 github-copilot)
        if api_type == 'github-copilot':
            url = config['base_url'].rstrip('/') + '/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {config['api_key']}",
                'Editor-Version': 'vscode/1.96.0',
                'Copilot-Integration-Id': 'vscode-chat',
            }
        else:
            url = config['base_url'].rstrip('/') + '/chat/completions'
            headers = {'Content-Type': 'application/json'}
            if config.get('api_key'):
                headers['Authorization'] = f"Bearer {config['api_key']}"
        payload = json.dumps({
            'model': config['model'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'max_tokens': max_tokens,
            'temperature': 0.9,
        }).encode()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data['choices'][0]['message']['content']
        except Exception as e:
            logger.warning('LLM call failed: %s', e)
            return None


def _llm_discuss(session: dict, user_message: str = None, decree: str = None) -> dict | None:
    """使用 LLM 生成多官员讨论。"""
    officials = session['officials']
    names = '、'.join(o['name'] for o in officials)

    profiles = ''
    for o in officials:
        profiles += f"\n### {o['name']}（{o['role']}）\n"
        profiles += f"职责范围：{o.get('duty', '综合事务')}\n"
        profiles += f"性格：{o['personality']}\n"
        profiles += f"说话风格：{o['speaking_style']}\n"

    # 构建最近的对话历史
    history = ''
    for msg in session['messages'][-20:]:
        if msg['type'] == 'system':
            history += f"\n【系统】{msg['content']}\n"
        elif msg['type'] == 'emperor':
            history += f"\n皇帝：{msg['content']}\n"
        elif msg['type'] == 'decree':
            history += f"\n【天命降临】{msg['content']}\n"
        elif msg['type'] == 'official':
            history += f"\n{msg.get('official_name', '?')}：{msg['content']}\n"
        elif msg['type'] == 'scene_note':
            history += f"\n（{msg['content']}）\n"

    if user_message:
        history += f"\n皇帝：{user_message}\n"
    if decree:
        history += f"\n【天命降临——上帝视角干预】{decree}\n"

    decree_section = ''
    if decree:
        decree_section = '\n请根据天命降临事件改变讨论走向，所有官员都必须对此做出反应。\n'

    prompt = f"""你是一个古代朝堂多角色群聊模拟器。模拟多位官员在朝堂上围绕议题的讨论。

## 参与官员
{names}

## 角色设定（每位官员都有明确的职责领域，必须从自身专业角度出发讨论）
{profiles}

## 当前议题
{session['topic']}

## 对话记录
{history if history else '（讨论刚刚开始）'}
{decree_section}
## 任务
生成每位官员的下一条发言。要求：
1. 每位官员说1-3句话，像真实朝堂讨论一样
2. **每位官员必须从自己的职责领域出发发言**——户部谈成本和数据、兵部谈安全和运维、工部谈技术实现、刑部谈质量和合规、礼部谈文档和规范、吏部谈人员安排、中书谈规划方案、门下谈审查风险、尚书谈执行调度、太子谈创新和大局，每个人关注的焦点不同
3. 官员之间要有互动——回应、反驳、支持、补充，尤其是不同部门的视角碰撞
4. 保持每位官员独特的说话风格和人格特征
5. 讨论要围绕议题推进、有实质性观点，不要泛泛而谈
6. 如果皇帝发言了，官员要恰当回应（但不要阿谀）
7. 可包含动作描写用*号*包裹（如 *拱手施礼*）

输出JSON格式：
{{
  "messages": [
    {{"official_id": "zhongshu", "name": "中书令", "content": "发言内容", "emotion": "neutral|confident|worried|angry|thinking|amused", "action": "可选动作描写"}},
    ...
  ],
  "scene_note": "可选的朝堂氛围变化（如：朝堂一片哗然|群臣窃窃私语），没有则为null"
}}

只输出JSON，不要其他内容。"""

    content = _llm_complete(
        '你是一个古代朝堂群聊模拟器，严格输出JSON格式。',
        prompt,
        max_tokens=1500,
    )

    if not content:
        return None

    # 解析 JSON
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0].strip()
    elif '```' in content:
        content = content.split('```')[1].split('```')[0].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning('Failed to parse LLM response: %s', content[:200])
        return None


def _llm_summarize(session: dict) -> str | None:
    """用 LLM 总结讨论结果。"""
    official_msgs = [m for m in session['messages'] if m['type'] == 'official']
    topic = session['topic']

    if not official_msgs:
        return None

    dialogue = '\n'.join(
        f"{m.get('official_name', '?')}：{m['content']}"
        for m in official_msgs[-30:]
    )

    prompt = f"""以下是朝堂官员围绕「{topic}」的讨论记录：

{dialogue}

请用2-3句话总结讨论结果、达成的共识和待决事项。用古风但简明的风格。"""

    return _llm_complete('你是朝堂记录官，负责总结朝议结果。', prompt, max_tokens=300)


# ── 规则模拟（无 LLM 时的降级方案）──

_SIMULATED_RESPONSES = {
    'stella': [
        '大家准备好了吗？让我们出发吧！这次冒险一定会成功的！',
        '作为团长，我认为我们应该制定一个详细的计划，确保每个环节都万无一失。',
        '*拔出剑指向远方* 目标就在前方，让我们一起征服它！',
    ],
    'lyra': [
        '团长～听我为您唱首歌吧，这是我为这次冒险创作的！',
        '这次冒险一定会成为传说的，我会把它写成最美丽的故事！',
        '*弹奏 lute* 让音乐为我们指引方向，为我们加油鼓劲！',
    ],
    'aria': [
        '团长～看我的魔法！这点小事交给我来处理吧',
        '从魔法角度来看，我们可以使用元素之力来解决这个问题。',
        '*挥动法杖* 元素之力，听我号令！',
    ],
    'sylvia': [
        '团长，前方发现情况，我们需要小心前进。',
        '我来为大家开路，熟悉野外的我会带领大家安全通过。',
        '*拉弓搭箭* 准备就绪，随时可以行动。',
    ],
    'nina': [
        '团长～看我新发明的药水！喝了它可以增加力量！',
        '这个配方一定会成功的，我已经测试过很多次了！',
        '*摇晃烧瓶* 看，颜色变了！这次肯定成功了！',
    ],
    'luna': [
        '团长～让我为您祝福，愿月光指引我们的道路',
        '从占卜结果来看，这次冒险会有挑战，但最终会成功。',
        '*举起法杖* 月光之力，保护我们的团队！',
    ],
    'kiana': [
        '团长～让我来保护您！任何敌人都别想靠近您！',
        '敌人交给我来对付，我会把他们全部打倒！',
        '*挥舞大剑* 准备战斗！为了团长，为了团队！',
    ],
    'mio': [
        '团长～我发现了一条秘密通道！可以节省很多时间！',
        '小心，前面有陷阱！让我先去侦察一下。',
        '*敏捷地跳上树顶* 我看到了，敌人在那边！',
    ],
    'hana': [
        '团长～让我为您疗伤，您的健康是最重要的',
        '大家都要平平安安的哦，我会一直守护着大家',
        '*拿出草药* 这个可以治疗伤口，效果很好的！',
    ],
    'yui': [
        '团长～机械装置已修复，现在可以正常运行了',
        '数据分析完毕，建议采取以下行动：先侦察，再制定计划',
        '*调整机械臂* 所有系统正常，可以开始行动了',
    ],
    'neko': [
        '团长～喵～发现敌人了！他们在那边！',
        '人家的耳朵可是很灵的哦♡ 任何动静都逃不过我的耳朵',
        '*轻盈地跳来跳去* 喵～我去侦察一下，马上回来！',
    ],
}

import random


def _simulated_discuss(session: dict, user_message: str = None, decree: str = None) -> list[dict]:
    """无 LLM 时的规则生成讨论内容。"""
    officials = session['officials']
    messages = []

    for o in officials:
        oid = o['id']
        pool = _SIMULATED_RESPONSES.get(oid, [])
        if isinstance(pool, set):
            pool = list(pool)
        if not pool:
            pool = ['臣附议。', '臣有不同看法。', '臣需要再想想。']

        content = random.choice(pool)
        emotions = ['neutral', 'confident', 'thinking', 'amused', 'worried']

        # 如果皇帝发言了或有天命降临，调整回应
        if decree:
            content = f'*面露惊色* 天命如此，{content}'
        elif user_message:
            content = f'回禀陛下，{content}'

        messages.append({
            'official_id': oid,
            'name': o['name'],
            'content': content,
            'emotion': random.choice(emotions),
            'action': None,
        })

    return messages


def _serialize(session: dict) -> dict:
    return {
        'ok': True,
        'session_id': session['session_id'],
        'topic': session['topic'],
        'task_id': session.get('task_id', ''),
        'officials': session['officials'],
        'messages': session['messages'],
        'round': session['round'],
        'phase': session['phase'],
    }
