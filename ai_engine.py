"""
AI 分析引擎 - 支持 Poe API (OpenAI兼容) 和 Anthropic 直连
"""
import json
import os
import re

import config
import stats as st


# ============================================================
# 统一调用层：自动选择 Poe 或 Anthropic
# ============================================================

def _call_llm(system_prompt, user_prompt, max_tokens=4000):
    """统一LLM调用接口，根据config自动选择API"""
    provider = config.API_PROVIDER.lower()

    if provider == "poe":
        return _call_poe(system_prompt, user_prompt, max_tokens)
    elif provider == "anthropic":
        return _call_anthropic(system_prompt, user_prompt, max_tokens)
    else:
        raise ValueError(f"未知的API_PROVIDER: {provider}，请在config.py中设置为 'poe' 或 'anthropic'")


def _call_poe(system_prompt, user_prompt, max_tokens=4000):
    """通过 Poe API 流式调用 (OpenAI兼容格式)，避免长时间思考超时"""
    import openai
    import time as _time

    api_key = config.POE_API_KEY or os.environ.get("POE_API_KEY", "")
    if not api_key:
        raise ValueError(
            "请设置 Poe API Key!\n"
            "编辑 config.py 填入 POE_API_KEY"
        )

    client = openai.OpenAI(
        api_key=api_key,
        base_url=config.POE_BASE_URL,
        timeout=600.0,  # 10分钟超时(含思考时间)
    )

    effort = getattr(config, "POE_OUTPUT_EFFORT", "high")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"      第{attempt}次重试...")

            # 使用流式响应，防止长思考导致连接超时
            params = dict(
                model=config.POE_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                extra_body={
                    "output_effort": effort,
                },
                stream=True,
            )
            if max_tokens and max_tokens > 0:
                params["max_tokens"] = max_tokens
            stream = client.chat.completions.create(**params)

            # 逐chunk收集完整回复
            chunks = []
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    chunks.append(chunk.choices[0].delta.content)

            result = "".join(chunks)
            if not result.strip():
                raise Exception("AI返回空内容")
            return result

        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            if attempt < max_retries:
                wait = attempt * 10
                print(f"      网络超时，{wait}秒后重试... ({attempt}/{max_retries})")
                _time.sleep(wait)
            else:
                raise Exception(f"连续{max_retries}次超时，请检查网络后重试") from e
        except Exception as e:
            err_msg = str(e).lower()
            # 处理Poe服务端断连(incomplete chunked read)
            if ("incomplete" in err_msg or "chunked" in err_msg or "peer closed" in err_msg) and attempt < max_retries:
                wait = attempt * 10
                print(f"      连接中断，{wait}秒后重试... ({attempt}/{max_retries})")
                _time.sleep(wait)
            else:
                raise


def _call_anthropic(system_prompt, user_prompt, max_tokens=4000):
    """通过 Anthropic 直连调用"""
    from anthropic import Anthropic

    api_key = config.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError(
            "请设置 Anthropic API Key!\n"
            "编辑 config.py 填入 ANTHROPIC_API_KEY"
        )

    import time as _time
    client = Anthropic(api_key=api_key, timeout=180.0)

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"      第{attempt}次重试...")
            response = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except Exception as e:
            if "timeout" in str(e).lower() and attempt < max_retries:
                wait = attempt * 10
                print(f"      超时，{wait}秒后重试... ({attempt}/{max_retries})")
                _time.sleep(wait)
            else:
                raise


# ============================================================
# System Prompt
# ============================================================

SYSTEM_PROMPT = """你是一位资深的福彩3D数据分析专家，擅长从历史开奖数据中发现统计规律和趋势。

你的分析原则：
1. 基于数据说话，所有结论必须有统计依据
2. 关注短期趋势(近10-30期)和中期规律(近50-100期)的结合
3. 重点分析：遗漏值回补、热冷号转换、和值区间震荡、形态轮换
4. 给出具体的过滤条件建议，可直接用于福彩3D霸主软件操作
5. 每个建议附带置信度(高/中/低)和依据
6. 区分"强信号"(多个指标共振)和"弱信号"(单一指标)

你擅长的分析方法：
- 遗漏值分析：号码长期未出现时的回补概率
- 热号追踪：连续活跃号码的持续性判断
- 和值走势：和值的区间震荡和趋势转折
- 形态分析：奇偶、大小、012路的轮换节奏
- AC值预判：号码离散度的规律
- 跨度分析：号码跨度的周期变化
- 重号规律：与上期号码的关联度

输出格式要求：使用中文，结构清晰，重点突出。"""


# ============================================================
# 功能模块
# ============================================================

def analyze_next_period(data, n_recent=50):
    """分析下一期，给出过滤策略建议"""
    full_stats = st.build_full_stats(data, n_recent)
    recent_detail = full_stats["近期开奖"][-20:]

    recent_15 = full_stats["近期开奖"][-15:]

    prompt = f"""分析福彩3D下一期过滤策略。最新:{full_stats['最新期号']}，基础:近{n_recent}期

近15期: {json.dumps(recent_15, ensure_ascii=False)}
号码频率: {json.dumps(full_stats['号码频率'], ensure_ascii=False)}
遗漏值: {json.dumps(full_stats['当前遗漏'], ensure_ascii=False)}
热温冷: {json.dumps(full_stats['热温冷号'], ensure_ascii=False)}
和值TOP: {json.dumps(dict(list(full_stats['和值分布'].items())[:10]), ensure_ascii=False)}
跨度: {json.dumps(full_stats['跨度分布'], ensure_ascii=False)}
奇偶比: {json.dumps(full_stats['奇偶比分布'], ensure_ascii=False)}
大小比: {json.dumps(full_stats['大小比分布'], ensure_ascii=False)}
AC值: {json.dumps(full_stats['AC值分布'], ensure_ascii=False)}
趋势: {json.dumps(full_stats['近10期趋势'], ensure_ascii=False)}

请简洁给出(总字数控制在800字以内)：
1. 趋势研判(热期/冷期/转换期，2-3句)
2. 百位/十位/个位各推荐4-5个号码(附简要理由)
3. 过滤条件: 和值、跨度、AC值、奇偶比、大小比
4. 胆码: 定位胆+不定位胆
5. 风险提示(1-2句)
6. 推荐直选5注"""

    return _call_llm(SYSTEM_PROMPT, prompt, max_tokens=2000)


# ============================================================
# 核心功能：AI分析 + 自动过滤一体化
# ============================================================

FILTER_SYSTEM_PROMPT = """你是一位资深的福彩3D数据分析专家。

你的任务是：基于历史数据分析，输出精确的过滤条件JSON，系统会自动执行过滤生成号码。

重要规则：
1. 基于数据的统计规律给出过滤条件，每个条件必须有依据
2. 最终过滤后注数应控制在 20-80 注之间（太少容易漏，太多没意义）
3. 如果条件过紧(预估<15注)就放宽条件；如果过松(预估>100注)就收紧条件
4. 优先使用置信度高的条件（位置号码、和值、跨度、AC值）
5. 你必须严格按照指定的JSON格式输出，不要遗漏任何字段
6. 投注方式为"直选"（百十个位顺序固定），不是组选！不要用组选类型过滤！
7. 组选类型字段必须留空[]，因为直选模式下组三/组六/豹子都可能中奖

JSON输出格式（必须严格遵守）：
```json
{
  "target_issue": "下一期期号",
  "analysis": "简要分析思路(2-3句话)",
  "confidence": "高/中/低",
  "filters": {
    "百位": [0,1,3,8],
    "十位": [1,2,5,7],
    "个位": [0,3,7,9],
    "和值": [11,12,13,14,15,16,17,18],
    "跨度": [4,5,6,7,8],
    "AC值": [2,3],
    "奇偶比": ["2:1","1:2"],
    "大小比": ["1:2","2:1"],
    "组选类型": [],
    "012路": [],
    "重号": {"上期号码": [2,6,1], "重号数": [0,1,2]},
    "必含号码": [],
    "和尾": [],
    "质合比": [],
    "连号": [],
    "首尾差": []
  },
  "key_reasons": [
    "理由1: ...",
    "理由2: ...",
    "理由3: ..."
  ],
  "risk_notes": ["风险点1", "风险点2"]
}
```

字段说明：
- 百位/十位/个位: 保留的号码列表，每位选4-6个号码
- 和值: 保留的和值列表(0-27)，通常选8-12个连续值
- 跨度: 保留的跨度列表(0-9)，通常选4-6个值
- AC值: 保留的AC值(0,1,2,3)
- 奇偶比: 格式为"奇数个数:偶数个数"，如"2:1"
- 大小比: 格式为"大号个数:小号个数"(>=5为大)，如"2:1"
- 组选类型: 直选模式，此项必须留空[]！不要填任何值！
- 012路: 三位各自除3余数组成的字符串，如"201"，留空=不过滤
- 重号: 上期号码+允许的重号个数
- 必含号码: 胆码(不定位)，留空=不设胆码
- 和尾: 和值的个位数(0-9)，留空=不过滤
- 质合比: 格式同奇偶比(1,2,3,5,7为质)，留空=不过滤
- 连号: 连号对数(0,1,2)，留空=不过滤
- 首尾差: 百位与个位差的绝对值(0-9)，留空=不过滤
- 不需要的条件留空数组[]即可

你的回复必须只包含一个JSON代码块，不要有其他内容。用```json开头，```结尾。"""


def analyze_and_filter(data, n_recent=50):
    """
    AI分析 + 自动过滤一体化
    返回: (ai_response_text, filter_conditions_dict, analysis_text)
    """
    full_stats = st.build_full_stats(data, n_recent)
    recent_detail = full_stats["近期开奖"][-20:]

    # 获取上期号码(用于重号)
    last = data[-1]
    prev_nums = [last["d1"], last["d2"], last["d3"]]

    # 计算下一期期号
    last_issue = last["issue"]
    next_issue_num = int(last_issue) + 1
    next_issue = str(next_issue_num)

    # 精简prompt: 只取最近10期详情 + 关键统计，减少AI思考时间
    recent_10 = full_stats["近期开奖"][-10:]

    prompt = f"""福彩3D {next_issue}期过滤条件。上期:{last['d1']}{last['d2']}{last['d3']}，上期号码:{prev_nums}

近10期: {json.dumps(recent_10, ensure_ascii=False)}

号码频率(近{n_recent}期): {json.dumps(full_stats['号码频率'], ensure_ascii=False)}
遗漏值: {json.dumps(full_stats['当前遗漏'], ensure_ascii=False)}
热温冷: {json.dumps(full_stats['热温冷号'], ensure_ascii=False)}
和值TOP: {json.dumps(dict(list(full_stats['和值分布'].items())[:10]), ensure_ascii=False)}
跨度: {json.dumps(full_stats['跨度分布'], ensure_ascii=False)}
奇偶比: {json.dumps(full_stats['奇偶比分布'], ensure_ascii=False)}
大小比: {json.dumps(full_stats['大小比分布'], ensure_ascii=False)}
AC值: {json.dumps(full_stats['AC值分布'], ensure_ascii=False)}
趋势: {json.dumps(full_stats['近10期趋势'], ensure_ascii=False)}

输出过滤条件JSON，目标20-80注。"""

    raw = _call_llm(FILTER_SYSTEM_PROMPT, prompt, max_tokens=4000)
    conditions = parse_filter_json(raw)
    return raw, conditions, next_issue


def parse_filter_json(ai_response):
    """从AI回复中提取JSON过滤条件"""
    # 尝试提取```json ... ```代码块
    match = re.search(r'```json\s*\n?(.*?)\n?\s*```', ai_response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # 尝试直接找 { ... } 最外层JSON
        match = re.search(r'\{[\s\S]*\}', ai_response)
        if match:
            json_str = match.group(0)
        else:
            raise ValueError("AI回复中未找到JSON过滤条件")

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {e}\n原文:\n{json_str[:500]}")

    # 提取filters字段
    filters = data.get("filters", data)
    analysis = data.get("analysis", "")
    confidence = data.get("confidence", "中")
    reasons = data.get("key_reasons", [])
    risks = data.get("risk_notes", [])

    return {
        "filters": filters,
        "analysis": analysis,
        "confidence": confidence,
        "key_reasons": reasons,
        "risk_notes": risks,
        "target_issue": data.get("target_issue", ""),
    }


def review_filter_result(data, gl_result, n_recent=30):
    """复盘分析：对比过滤结果与开奖号码"""
    issue = gl_result.get("issue", "未知")
    filter_numbers = gl_result["numbers"]
    filter_count = gl_result["count"]

    actual = None
    for d in data:
        if d["issue"] == issue:
            actual = d
            break

    issue_idx = None
    for i, d in enumerate(data):
        if d["issue"] == issue:
            issue_idx = i
            break

    context_data = []
    if issue_idx is not None:
        start = max(0, issue_idx - 10)
        end = min(len(data), issue_idx + 3)
        for i in range(start, end):
            d = data[i]
            marker = " ← 当期" if i == issue_idx else ""
            context_data.append(f"{d['issue']}期: {d['d1']}{d['d2']}{d['d3']}{marker}")

    hit_info = "未找到该期开奖数据"
    if actual:
        actual_tuple = (actual["d1"], actual["d2"], actual["d3"])
        if actual_tuple in filter_numbers:
            hit_info = f"✓ 命中！开奖号码 {actual['d1']}{actual['d2']}{actual['d3']} 在过滤结果中"
        else:
            hit_info = f"✗ 未命中。开奖号码 {actual['d1']}{actual['d2']}{actual['d3']} 不在过滤结果中"

    from collections import Counter
    sum_c = Counter()
    span_c = Counter()
    oe_c = Counter()
    for n in filter_numbers:
        sum_c[st.calc_sum(*n)] += 1
        span_c[st.calc_span(*n)] += 1
        oe_c[st.calc_odd_even(*n)] += 1

    prompt = f"""请复盘分析以下福彩3D过滤结果。

## 基本信息
- 期号: {issue}
- 文件: {gl_result.get('filename', '未知')}
- 过滤结果: {filter_count}注 ({gl_result['type']})
- 命中情况: {hit_info}

## 前后期走势
{chr(10).join(context_data)}

## 过滤结果号码
{', '.join(f'{n[0]}{n[1]}{n[2]}' for n in filter_numbers[:50])}
{'...(共' + str(len(filter_numbers)) + '注)' if len(filter_numbers) > 50 else ''}

## 过滤结果特征
- 和值分布: {dict(sum_c.most_common(10))}
- 跨度分布: {dict(span_c.most_common())}
- 奇偶比分布: {dict(oe_c.most_common())}

请分析：
1. 本次过滤效果评价（注数是否合理、覆盖面如何）
2. 如果未命中，分析可能是哪个过滤条件过于激进导致号码被淘汰
3. 过滤结果的号码分布是否存在明显偏差
4. 对下次过滤策略的改进建议"""

    return _call_llm(SYSTEM_PROMPT, prompt, max_tokens=3000)


def chat_analysis(data, user_question, n_recent=30):
    """对话式分析 - 用户自由提问"""
    full_stats = st.build_full_stats(data, n_recent)
    recent_detail = full_stats["近期开奖"][-15:]

    prompt = f"""用户提问: {user_question}

## 参考数据 (最近15期)
{json.dumps(recent_detail, ensure_ascii=False, indent=1)}

## 号码遗漏值
{json.dumps(full_stats['当前遗漏'], ensure_ascii=False)}

## 热温冷号
{json.dumps(full_stats['热温冷号'], ensure_ascii=False)}

## 和值分布
{json.dumps(full_stats['和值分布'], ensure_ascii=False)}

## 近10期趋势
{json.dumps(full_stats['近10期趋势'], ensure_ascii=False)}

请基于数据回答用户的问题。"""

    return _call_llm(SYSTEM_PROMPT, prompt, max_tokens=3000)


def batch_review(data, gl_files, max_files=20):
    """批量复盘多期过滤结果，统计命中率"""
    results = []
    hit_count = 0
    total = 0

    for gl in gl_files[-max_files:]:
        issue = gl.get("issue", "")
        if not issue:
            continue

        actual = None
        for d in data:
            if d["issue"] == issue:
                actual = d
                break

        if actual is None:
            continue

        actual_tuple = (actual["d1"], actual["d2"], actual["d3"])
        hit = actual_tuple in gl["numbers"]

        if hit:
            hit_count += 1
        total += 1

        results.append({
            "期号": issue,
            "文件": gl["filename"],
            "注数": gl["count"],
            "开奖号码": f"{actual['d1']}{actual['d2']}{actual['d3']}",
            "命中": "✓" if hit else "✗",
        })

    summary = f"共{total}期, 命中{hit_count}期, 命中率{hit_count / total * 100:.1f}%" if total > 0 else "无可复盘数据"

    if total > 0:
        prompt = f"""请分析以下福彩3D过滤结果的批量复盘数据。

## 汇总
{summary}

## 详细记录
{json.dumps(results, ensure_ascii=False, indent=1)}

请分析：
1. 整体命中率评价
2. 未命中期的共同特征（注数过少？开奖号码是否属于冷门？）
3. 命中期的特征（什么注数范围命中率最高？）
4. 改进建议"""

        ai_analysis = _call_llm(SYSTEM_PROMPT, prompt, max_tokens=3000)
    else:
        ai_analysis = "无足够数据进行AI分析"

    return {
        "summary": summary,
        "results": results,
        "ai_analysis": ai_analysis,
    }
