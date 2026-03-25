"""
数据管理模块 - 下载/更新/加载福彩3D开奖数据 + 解析GL过滤文件
"""
import os
import csv
import re
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

import config


def download_history(year_start=2003, year_end=None):
    """从中彩网下载福彩3D历史数据"""
    if requests is None:
        print("[错误] 需要 requests: pip install requests")
        return []
    if year_end is None:
        year_end = datetime.now().year

    all_data = []
    print(f"正在下载 {year_start}-{year_end} 年数据...")
    for year in range(year_start, year_end + 1):
        url = (
            f"https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
            f"?name=3d&issueStart={year}001&issueEnd={year}366"
            f"&pageNo=1&pageSize=400&systemType=PC"
        )
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.cwl.gov.cn/ygkj/3d/kjgg/",
                "Accept": "application/json",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                records = resp.json().get("result", [])
                for r in records:
                    issue = r.get("code", "")
                    numbers = r.get("red", "")
                    date = r.get("date", "")
                    if issue and numbers:
                        sep = "," if "," in numbers else " "
                        digits = numbers.strip().split(sep)
                        if len(digits) == 3:
                            all_data.append({
                                "issue": issue, "date": date,
                                "d1": int(digits[0]),
                                "d2": int(digits[1]),
                                "d3": int(digits[2]),
                            })
                print(f"  {year}年: {len(records)}期")
            else:
                print(f"  {year}年: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  {year}年: 失败 - {e}")

    all_data.sort(key=lambda x: x["issue"])
    return all_data


def save_csv(data, filepath=None):
    filepath = filepath or config.HISTORY_CSV
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["issue", "date", "d1", "d2", "d3"])
        writer.writeheader()
        writer.writerows(data)
    print(f"已保存 {len(data)} 期 → {filepath}")


def load_csv(filepath=None):
    filepath = filepath or config.HISTORY_CSV
    if not os.path.exists(filepath):
        return []
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["d1"] = int(row["d1"])
            row["d2"] = int(row["d2"])
            row["d3"] = int(row["d3"])
            data.append(row)
    return data


def load_or_download():
    data = load_csv()
    if data:
        print(f"已加载: {len(data)}期 (最新: {data[-1]['issue']}期)")
        return data
    print("本地无数据，开始下载...")
    data = download_history()
    if data:
        save_csv(data)
    return data


def update_data(existing_data=None):
    """增量更新数据，返回(全量数据, 新增条数)"""
    if existing_data is None:
        existing_data = load_csv()
    if not existing_data:
        data = download_history()
        if data:
            save_csv(data)
        return data, len(data)

    last_year = int(existing_data[-1]["issue"][:4])
    current_year = datetime.now().year
    new_data = download_history(year_start=last_year, year_end=current_year)
    existing_issues = {d["issue"] for d in existing_data}
    added = [d for d in new_data if d["issue"] not in existing_issues]

    if added:
        existing_data.extend(added)
        existing_data.sort(key=lambda x: x["issue"])
        save_csv(existing_data)
        print(f"新增 {len(added)} 期")
    else:
        print("数据已是最新")

    return existing_data, len(added)


def fetch_today_result():
    """获取今天的开奖结果，返回 dict 或 None"""
    if requests is None:
        return None
    today = datetime.now()
    year = today.year
    url = (
        f"https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
        f"?name=3d&issueCount=1&pageNo=1&pageSize=1&systemType=PC"
    )
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.cwl.gov.cn/ygkj/3d/kjgg/",
            "Accept": "application/json",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            records = resp.json().get("result", [])
            if records:
                r = records[0]
                issue = r.get("code", "")
                numbers = r.get("red", "")
                date = r.get("date", "")
                if issue and numbers:
                    sep = "," if "," in numbers else " "
                    digits = numbers.strip().split(sep)
                    if len(digits) == 3:
                        return {
                            "issue": issue, "date": date,
                            "d1": int(digits[0]),
                            "d2": int(digits[1]),
                            "d3": int(digits[2]),
                        }
    except Exception as e:
        print(f"获取开奖失败: {e}")
    return None


def parse_gl_file(filepath):
    """解析GL过滤结果文件(兼容有逗号和无逗号两种格式)"""
    with open(filepath, "rb") as f:
        raw = f.read()
    text = raw.decode("gb18030", errors="replace")
    lines = text.strip().split("\n")

    result = {"header": "", "numbers": [], "count": 0, "type": "直选"}
    if lines:
        header = lines[0].strip()
        result["header"] = header
        m = re.search(r"(\d{7})期", header)
        if m:
            result["issue"] = m.group(1)
        m = re.search(r"共(\d+)注", header)
        if m:
            result["count"] = int(m.group(1))
        if "组选" in header:
            result["type"] = "组选"

    for line in lines[1:]:
        line = line.strip()
        # 格式1: "6,3,7" (有逗号)
        if re.match(r"^\d,\d,\d$", line):
            d1, d2, d3 = line.split(",")
            result["numbers"].append((int(d1), int(d2), int(d3)))
        # 格式2: "637" (无逗号，3位数字)
        elif re.match(r"^\d{3}$", line):
            result["numbers"].append((int(line[0]), int(line[1]), int(line[2])))

    return result


def load_gl_files(gl_dir=None):
    """加载所有GL过滤结果文件"""
    if gl_dir is None:
        gl_dir = os.path.join(config.OUTPUT_DIR, "gl")
    if not os.path.exists(gl_dir):
        return []
    results = []
    for f in sorted(os.listdir(gl_dir)):
        if f.startswith("GL") and f.endswith(".txt"):
            try:
                parsed = parse_gl_file(os.path.join(gl_dir, f))
                parsed["filename"] = f
                results.append(parsed)
            except Exception as e:
                print(f"  解析 {f} 失败: {e}")
    return results


def manual_input_data():
    existing = load_csv()
    existing_issues = {d["issue"] for d in existing}
    print("手动输入 (格式: 期号 百 十 个, 如 2026073 6 3 7, 输入q结束):")
    while True:
        line = input("> ").strip()
        if line.lower() == "q":
            break
        parts = line.split()
        if len(parts) == 4:
            issue, d1, d2, d3 = parts
            if issue not in existing_issues:
                existing.append({"issue": issue, "date": "", "d1": int(d1), "d2": int(d2), "d3": int(d3)})
                existing_issues.add(issue)
                print(f"  +{issue}期 {d1}{d2}{d3}")
            else:
                print(f"  {issue}期已存在")
        else:
            print("  格式错误")
    existing.sort(key=lambda x: x["issue"])
    save_csv(existing)
    return existing
