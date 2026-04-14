"""30种策略回测对比"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import data_manager as dm
from collections import Counter
from math import comb

data = dm.load_or_download()
test_periods = 300
test_start = len(data) - test_periods

def score_digits(history, method):
    freq10 = Counter()
    freq20 = Counter()
    freq30 = Counter()
    freq50 = Counter()
    for d in history[-10:]:
        for x in [d['d1'],d['d2'],d['d3']]: freq10[x] += 1
    for d in history[-20:]:
        for x in [d['d1'],d['d2'],d['d3']]: freq20[x] += 1
    for d in history[-30:]:
        for x in [d['d1'],d['d2'],d['d3']]: freq30[x] += 1
    for d in history[-50:]:
        for x in [d['d1'],d['d2'],d['d3']]: freq50[x] += 1

    recent = history[-100:]
    due = {}
    for digit in range(10):
        apps = [j for j,d in enumerate(recent) if digit in (d['d1'],d['d2'],d['d3'])]
        if len(apps)>=2:
            avg = sum(apps[k]-apps[k-1] for k in range(1,len(apps)))/(len(apps)-1)
        else:
            avg = 50
        cur = len(recent)-1-apps[-1] if apps else 50
        due[digit] = cur/avg if avg>0 else 0

    prev = [history[-1]['d1'],history[-1]['d2'],history[-1]['d3']]
    adj = set()
    for d in prev:
        adj.add((d-1)%10)
        adj.add((d+1)%10)
    prev2 = [history[-2]['d1'],history[-2]['d2'],history[-2]['d3']] if len(history)>=2 else prev

    scores = {}
    for digit in range(10):
        if method == 1: s = freq30[digit]
        elif method == 2: s = freq10[digit]
        elif method == 3: s = freq50[digit]
        elif method == 4: s = due[digit]
        elif method == 5: s = freq30[digit]*0.5 + due[digit]*3
        elif method == 6: s = freq10[digit] + (3 if digit in adj else 0)
        elif method == 7: s = freq30[digit] + (3 if digit in adj else 0)
        elif method == 8: s = due[digit]*3 + (2 if digit in adj else 0)
        elif method == 9: s = freq30[digit]*0.3 + due[digit]*2 + (2 if digit in adj else 0)
        elif method == 10: s = -freq30[digit] + due[digit]*5
        elif method == 11: s = (5 if digit in prev else 0) + (3 if digit in adj else 0)
        elif method == 12: s = (3 if digit in prev else 0) + (2 if digit in prev2 else 0) + freq10[digit]*0.5
        elif method == 13: s = freq20[digit]*0.4 + due[digit]*2.5
        elif method == 14: s = 10 if digit in adj else 0
        elif method == 15: s = freq10[digit]*2 + freq20[digit]*0.5
        elif method == 16: s = due[digit]*10
        elif method == 17: s = freq50[digit]*0.2 + due[digit]*2
        elif method == 18: s = freq10[digit]*0.3 + freq30[digit]*0.2 + due[digit]*1.5 + (1.5 if digit in adj else 0)
        elif method == 19: s = (4 if digit in prev else 0) + freq30[digit]*0.3
        elif method == 20: s = freq30[digit] + (2 if digit%2==1 else 0)
        elif method == 21: s = freq30[digit] + (2 if digit%2==0 else 0)
        elif method == 22: s = freq30[digit] + (2 if digit>=5 else 0)
        elif method == 23: s = freq30[digit] + (2 if digit<5 else 0)
        elif method == 24: s = freq30[digit] + (2 if digit in {1,2,3,5,7} else 0)
        elif method == 25:
            r10 = freq10[digit]/max(sum(freq10.values()),1)*10
            r50 = freq50[digit]/max(sum(freq50.values()),1)*10
            s = (r10-r50)*5 + freq30[digit]*0.2
        elif method == 26:
            pf = Counter()
            for d in history[-30:]:
                pf[d['d1']] += 1.2; pf[d['d2']] += 1.0; pf[d['d3']] += 0.8
            s = pf.get(digit,0)
        elif method == 27:
            comp = Counter()
            for d in history[-50:]:
                digits = [d['d1'],d['d2'],d['d3']]
                for x in digits:
                    for y in digits:
                        if x!=y: comp[(x,y)] += 1
            hot3 = [d for d,_ in freq30.most_common(3)]
            s = 0
            for h in hot3:
                s += comp.get((h,digit),0)*0.3
        elif method == 28: s = freq30[digit]*0.25 + due[digit]*1.5 + (2 if digit in adj else 0) + (1.5 if digit in prev else 0)
        elif method == 29:
            sums = [d['d1']+d['d2']+d['d3'] for d in history[-10:]]
            std = (sum((sv-sum(sums)/10)**2 for sv in sums)/10)**0.5
            s = freq10[digit]*2 if std < 3 else freq50[digit]*0.5 + due[digit]*2
        elif method == 30:
            s = (freq10[digit]*0.2 + freq20[digit]*0.15 + freq30[digit]*0.1 +
                 due[digit]*1.5 + (1.5 if digit in adj else 0) + (1 if digit in prev else 0) +
                 (0.5 if digit in prev2 else 0))
        else: s = 0
        scores[digit] = s

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

names = {
    1:"freq30", 2:"freq10", 3:"freq50", 4:"pure_due", 5:"f30+due",
    6:"f10+adj", 7:"f30+adj", 8:"due+adj", 9:"f30+due+adj",
    10:"cold_rev", 11:"prev+adj", 12:"prev2+f10", 13:"f20+due",
    14:"pure_adj", 15:"hot_chase", 16:"max_due", 17:"f50+due",
    18:"wt_multi", 19:"prev+f30", 20:"odd_pref", 21:"even_pref",
    22:"big_pref", 23:"small_pref", 24:"prime_pref", 25:"freq_diff",
    26:"pos_wt", 27:"companion", 28:"f+d+a+p", 29:"dyn_win",
    30:"all_dims"
}

results = []
total_combos = len(names) * 3
done = 0

for method in range(1, 31):
    for n_sel in [5, 6, 7]:
        g6_hits = 0
        g3_hits = 0

        for i in range(test_start, len(data)):
            history = data[:i]
            actual = data[i]
            actual_set = set([actual['d1'],actual['d2'],actual['d3']])

            ranked = score_digits(history, method)
            top_set = set(d for d,_ in ranked[:n_sel])

            if actual_set <= top_set:
                if len(actual_set)==3: g6_hits += 1
                elif len(actual_set)==2: g3_hits += 1

        g6_cost = comb(n_sel,3)*2
        g3_cost = n_sel*(n_sel-1)*2
        total_hits = g6_hits + g3_hits
        total_prize = g6_hits*160 + g3_hits*346
        total_cost = (g6_cost+g3_cost)*test_periods
        net = total_prize - total_cost
        hr = total_hits/test_periods*100

        results.append((method, n_sel, total_hits, hr, g6_hits, g3_hits, total_prize, total_cost, net))
        done += 1
        if done % 10 == 0:
            print(f"Progress: {done}/{total_combos}", flush=True)

results.sort(key=lambda x: x[2], reverse=True)

print()
print(f"{'#':>3} {'strategy':>15} {'N':>2} {'hits':>4} {'rate':>6} {'G6':>3} {'G3':>3} {'prize':>6} {'cost':>6} {'net':>7}")
print("-"*62)
for r in results[:40]:
    m,n,h,hr,g6,g3,prize,cost,net = r
    mark = " WIN" if net > 0 else ""
    print(f"{m:>3} {names[m]:>15} {n:>2}  {h:>4} {hr:>5.1f}% {g6:>3} {g3:>3} {prize:>6} {cost:>6} {net:>+7}{mark}")
