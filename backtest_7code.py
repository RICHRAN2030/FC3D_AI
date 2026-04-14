"""6组七码动态选择回测"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_manager as dm
from collections import Counter
from math import comb

data = dm.load_or_download()

groups = {
    "A": {0,1,2,3,4,8,9},
    "B": {0,3,4,5,6,7,9},
    "C": {0,1,5,6,7,8,9},
    "D": {1,2,3,4,5,6,7},
    "E": {0,2,4,5,6,7,8},
    "F": {2,3,5,6,7,8,9},
}

print("6 groups:")
for n, g in groups.items():
    ex = sorted(set(range(10)) - g)
    print(f"  {n}: {sorted(g)} exclude {ex}")
print()

test_periods = 500
test_start = len(data) - test_periods
bets_per_group = comb(7, 3)  # 35
cost_per_group = bets_per_group * 2  # 70

# 1. Fixed group hit rates
print(f"=== Fixed group hit rates ({test_periods} periods) ===")
for name, g in groups.items():
    hits = 0
    g6 = 0
    for i in range(test_start, len(data)):
        d = data[i]
        s = {d['d1'], d['d2'], d['d3']}
        if len(s) != 3: continue
        g6 += 1
        if s <= g: hits += 1
    hr = hits/g6*100
    net = hits*160 - cost_per_group*test_periods
    print(f"  {name}: {hits}/{g6}={hr:.1f}% net={net:+d}")
print()

# 2. Score function
def score_groups(history, groups):
    f5 = Counter(); f10 = Counter(); f30 = Counter()
    for d in history[-5:]:
        for x in [d['d1'],d['d2'],d['d3']]: f5[x]+=1
    for d in history[-10:]:
        for x in [d['d1'],d['d2'],d['d3']]: f10[x]+=1
    for d in history[-30:]:
        for x in [d['d1'],d['d2'],d['d3']]: f30[x]+=1
    recent = history[-100:]
    due = {}
    for digit in range(10):
        apps = [j for j,d in enumerate(recent) if digit in (d['d1'],d['d2'],d['d3'])]
        if len(apps)>=2:
            avg = sum(apps[k]-apps[k-1] for k in range(1,len(apps)))/(len(apps)-1)
        else: avg = 50
        cur = len(recent)-1-apps[-1] if apps else 50
        due[digit] = cur/avg if avg>0 else 0
    prev = set([history[-1]['d1'],history[-1]['d2'],history[-1]['d3']])
    adj = set()
    for d in prev: adj.add((d-1)%10); adj.add((d+1)%10)

    scores = {}
    for name, g in groups.items():
        score = 0
        for digit in g:
            score += f5.get(digit,0)*0.3 + f10.get(digit,0)*0.15 + f30.get(digit,0)*0.05
            score += due.get(digit,0)*1.5
            if digit in adj: score += 1
            if digit in prev: score += 0.5
        scores[name] = score
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

# 3. Dynamic strategies
print("=== Dynamic selection strategies ===")
for n_groups in [1, 2, 3, 4, 5, 6]:
    hits = 0
    multi = 0
    g6_total = 0

    for i in range(test_start, len(data)):
        history = data[:i]
        d = data[i]
        actual_set = {d['d1'], d['d2'], d['d3']}
        if len(actual_set) != 3: continue
        g6_total += 1

        ranked = score_groups(history, groups)
        chosen = [name for name, _ in ranked[:n_groups]]

        h = sum(1 for c in chosen if actual_set <= groups[c])
        if h > 0: hits += 1
        multi += max(0, h - 1)

    cost = cost_per_group * n_groups * test_periods
    prize = (hits + multi) * 160
    net = prize - cost
    hr = hits/g6_total*100
    per = net / test_periods
    print(f"  Top {n_groups}: {hits}/{g6_total}={hr:.1f}% cost={cost} prize={prize} net={net:+d} ({per:+.1f}/d) {'WIN' if net>0 else 'loss'}")

# 4. Show recent 30 periods detail for top-1 strategy
print()
print("=== Recent 30 periods (dynamic top-1) ===")
for i in range(len(data)-30, len(data)):
    history = data[:i]
    d = data[i]
    actual_set = {d['d1'], d['d2'], d['d3']}
    ranked = score_groups(history, groups)
    chosen = ranked[0][0]
    hit = len(actual_set)==3 and actual_set <= groups[chosen]
    g_type = "G6" if len(actual_set)==3 else "G3" if len(actual_set)==2 else "BZ"
    status = "HIT!" if hit else ("skip" if g_type!="G6" else "miss")
    print(f"  {d['issue']} {d['d1']}{d['d2']}{d['d3']} {g_type} -> {chosen}{sorted(groups[chosen])} {status}")
