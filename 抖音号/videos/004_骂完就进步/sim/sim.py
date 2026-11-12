"""004 仿真：1000 个孩子考两次试。分数 = 实力 + 当天的运气。两次考试之间没有任何人被夸或被骂，实力不变。
看：第一次考得最差的 100 人，第二次有多少进步；考得最好的 100 人，第二次有多少退步。
python3 sim.py  -> 打印结果，写 result.json（seed=4 那一遍给画面用）"""
import json, numpy as np
N=1000; MU=70; SD_ABILITY=8; SD_LUCK=8; K=100
def run(seed, sd_luck=SD_LUCK):
    r=np.random.default_rng(seed)
    a=r.normal(MU,SD_ABILITY,N); l1=r.normal(0,sd_luck,N); l2=r.normal(0,sd_luck,N)
    t1=np.clip(a+l1,0,100); t2=np.clip(a+l2,0,100)
    o=np.argsort(t1); bot=o[:K]; top=o[-K:]
    return dict(seed=seed,
      bot_up=int((t2[bot]>t1[bot]).sum()), bot_gain=float((t2[bot]-t1[bot]).mean()), bot_t1=float(t1[bot].mean()), bot_t2=float(t2[bot].mean()),
      top_down=int((t2[top]<t1[top]).sum()), top_drop=float((t1[top]-t2[top]).mean()), top_t1=float(t1[top].mean()), top_t2=float(t2[top].mean()),
      bot_luck=float(l1[bot].mean()), top_luck=float(l1[top].mean()),
      all_up=int((t2>t1).sum())), dict(a=a,t1=t1,t2=t2,l1=l1)
if __name__=="__main__":
    rs=[run(s)[0] for s in range(1,31)]
    for k in ("bot_up","top_down","bot_gain","top_drop","all_up"):
        v=[x[k] for x in rs]; print(k, "min %.1f max %.1f mean %.1f"%(min(v),max(v),sum(v)/len(v)))
    for sl in (4,8,12):
        v=[run(s,sl)[0] for s in range(1,31)]
        print("luck sd",sl,"bot_up",min(x["bot_up"] for x in v),max(x["bot_up"] for x in v),"top_down",min(x["top_down"] for x in v),max(x["top_down"] for x in v))
    for s in range(1,9):
        print(run(s)[0])

def export(seed=3, path="result.json"):
    res, d = run(seed)
    t1, t2 = d["t1"], d["t2"]
    o = np.argsort(t1); grp = np.zeros(N, int); grp[o[:K]] = 1; grp[o[-K:]] = 2
    # “你”：最差 100 人里，两次分数最接近片子开头那两张卷子（55 → 71）的那个孩子。
    # 这是特意挑的一个人，不代表这组的平均：这组平均进步约 11 分，他进步约 15 分。
    bot = o[:K]; gain = t2[bot] - t1[bot]
    you = int(bot[np.argmin(np.abs(t1[bot] - 55) + np.abs(t2[bot] - 71))])
    res["bot_gain_over15"] = int((gain > 15).sum())
    res["you"] = dict(t1=float(t1[you]), t2=float(t2[you]))
    json.dump(dict(summary=res, you=you, t1=[round(float(x), 2) for x in t1], t2=[round(float(x), 2) for x in t2], grp=grp.tolist()),
              open(path, "w"))
    print("export", res)
if __name__ == "__main__":
    export()
