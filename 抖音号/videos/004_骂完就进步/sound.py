"""004 的声音：全部用 numpy 合成（不配音、不用别人的音乐）。
读 out/frames/meta.json 里的时间表和事件表（出自 scene.html），写 out/mix.wav。
python3 sound.py"""
import json, wave, numpy as np
SR = 48000
meta = json.load(open("out/frames/meta.json")); DUR = meta["frames"] / meta["fps"]; T = meta["T"]
N = int(DUR * SR); rng = np.random.default_rng(4)

def env(n, a=.005, d=.3):
    t = np.arange(n) / SR; return np.minimum(t / a, 1) * np.exp(-t / d)
def tone(f, dur, a=.005, d=.3, harm=(1, .3, .1)):
    n = int(dur * SR); t = np.arange(n) / SR
    return sum(h * np.sin(2 * np.pi * f * (k + 1) * t) for k, h in enumerate(harm)) * env(n, a, d)
def noise(dur, lo, hi):
    n = int(dur * SR); X = np.fft.rfft(rng.normal(0, 1, n)); f = np.fft.rfftfreq(n, 1 / SR); X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n)
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def put(buf, x, t, g=1.0):
    i = int(t * SR); j = min(N, i + len(x))
    if 0 <= i < N: buf[i:j] += g * x[:j - i]
def sweep(dur, f0, f1):                      # 一阵风：低通的截止频率从 f0 滑到 f1
    n = int(dur * SR); x = rng.normal(0, 1, n); t = np.linspace(0, 1, n); out = np.zeros(n); y = 0.0
    al = 1 - np.exp(-2 * np.pi * (f0 * (f1 / f0) ** t) / SR)
    for k in range(n): y += al[k] * (x[k] - y); out[k] = y
    return out * np.sin(np.pi * t) ** 1.5

sfx = np.zeros(N); mus = np.zeros(N)
def ev(name, t):
    if name == 'thud':
        put(sfx, tone(90, .5, .004, .16, (1, .6, .4, .2)), t, .8); put(sfx, noise(.06, 200, 2000) * env(int(.06 * SR), .002, .02), t, .25)
    elif name == 'tick': put(sfx, tone(hz(76), .25, .003, .08), t, .35)
    elif name == 'dun':                      # 大人那句话：两声往下走的低音
        put(sfx, tone(hz(62), .45, .01, .18, (1, .5, .25)), t, .42); put(sfx, tone(hz(57), .6, .01, .25, (1, .5, .25)), t + .16, .42)
    elif name == 'q': put(sfx, tone(hz(72), .3, .005, .12), t, .4); put(sfx, tone(hz(79), .5, .005, .2), t + .14, .4)
    elif name == 'rain':                     # 一千个点落下：密密的小木珠声
        for k in range(150):
            put(sfx, tone(hz(rng.choice([72, 76, 79, 81, 84, 88])), .12, .002, .035, (1, .2)), t + rng.uniform(0, 2.0), .07)
    elif name in ('mark', 'mark2'):
        a, b = (64, 67) if name == 'mark' else (67, 71)
        put(sfx, tone(hz(a), .4, .004, .15), t, .4); put(sfx, tone(hz(b), .5, .004, .2), t + .1, .4)
    elif name == 'you': put(sfx, tone(hz(88), .9, .003, .35, (1, .4, .2, .1)), t, .3)
    elif name == 'whoosh': put(sfx, sweep(1.4, 300, 3000), t, .5)
    elif name in ('count_up', 'count_down'):
        seq = [60, 62, 64, 67, 69, 72, 76, 79] if name == 'count_up' else [84, 81, 79, 76, 72, 69, 67, 64]
        for k, m in enumerate(seq): put(sfx, tone(hz(m), .2, .003, .07), t + k * .09, .3)
        put(sfx, tone(hz(84 if name == 'count_up' else 57), .9, .004, .35, (1, .4, .2)), t + .78, .4)
    elif name == 'soft': put(sfx, tone(hz(57), .9, .02, .4, (1, .3, .1)), t, .3)
    elif name == 'page': put(sfx, noise(.35, 800, 6000) * np.sin(np.pi * np.linspace(0, 1, int(.35 * SR))) ** 2, t, .12)
    elif name in ('p', 'plow', 'phigh'):
        put(sfx, tone(hz({'p': 69, 'plow': 62, 'phigh': 81}[name]), .5, .003, .16, (1, .35, .12)), t, .42)
    elif name == 'tag':
        put(sfx, tone(hz(91), .18, .002, .05, (1, .3)), t, .3); put(sfx, noise(.03, 1000, 5000) * env(int(.03 * SR), .001, .01), t, .2)
    elif name in ('chord', 'chord2'):
        for m in ((48, 55, 60, 64, 67, 72) if name == 'chord' else (53, 57, 60, 65, 69, 72)):
            put(sfx, tone(hz(m), 3.5, .03, 1.3, (1, .3, .1)), t, .16)
    elif name == 'q2': put(sfx, tone(hz(67), .5, .005, .2), t, .4); put(sfx, tone(hz(74), 1.2, .005, .5), t + .25, .4)
    elif name in ('opt', 'opt2'): put(sfx, tone(hz(79 if name == 'opt' else 83), .3, .002, .1, (1, .4)), t, .4)
    else: raise SystemExit("没有这个音效：" + name)
for t, name in meta["sfx"]: ev(name, t)

# 配乐：很轻的拇指琴琶音，96 拍。低音放在 130–220 Hz（再低手机喇叭放不出来）。开头只有低音，仿真段起琶音，讲原因那段变稀，结尾停在没解决的和弦上
BEAT = 60 / 96
def arp(t0, t1, chords, g, step=.5, pat=(0, 2, 1, 2)):
    t = t0; k = 0
    while t < t1 - .05:
        ch = chords[int((t - t0) / (BEAT * 4)) % len(chords)]
        put(mus, tone(hz(ch[pat[k % len(pat)]] + 12), .6, .004, .22, (1, .25, .08)), t, g)
        if abs((t - t0) % (BEAT * 4)) < 1e-6 or k == 0: put(mus, tone(hz(ch[0]), BEAT * 4, .03, 1.2, (1, .3, .1)), t, g * .9)
        t += BEAT * step; k += 1
Am = (57, 60, 64); F = (53, 57, 60); C = (48, 52, 55); G = (55, 59, 62)
for t in (0, T["l2"], T["bub"] + .6): put(mus, tone(hz(57), 1.2, .03, .5, (1, .3, .1)), t, .16)
arp(T["pile"], T["why"], [Am, F, C, G], .11)
arp(T["why"] + .5, T["take"], [F, C, Am, G], .08, step=1.0, pat=(0, 1, 2, 1))
arp(T["q"] + .3, DUR - 1.2, [F, G], .07, step=1.0)

mix = sfx + mus; fo = int(.8 * SR); mix[-fo:] *= np.linspace(1, 0, fo)
mix = np.tanh(mix * 1.2); mix /= max(1e-9, np.abs(mix).max()) / .7
st = (np.stack([mix, mix], 1) * 32767).astype('<i2')
w = wave.open("out/mix.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes()); w.close()
# 自查：每秒的响度（dBFS），看有没有哪一秒空着或者爆掉
sec = [20 * np.log10(max(1e-6, np.sqrt(np.mean(mix[i * SR:(i + 1) * SR] ** 2)))) for i in range(int(DUR))]
print("时长 %.1f 秒；每秒 RMS（dBFS）：" % DUR, " ".join("%.0f" % x for x in sec))
