import sys, time, shutil, json, subprocess, urllib.request
from gradio_client import Client
D='.'  # folder containing portrait.png (copy input_portrait_704x1216.png to portrait.png)
O='.'
STYLE='cute fluffy blue baby finless porpoise mascot, 3D Pixar style, soft warm lighting, old brick street with steaming breakfast stall in background, static camera'
A={'C2':'the porpoise is suddenly startled by a loud shout, jumps back, eyes wide open in shock, body trembling, sweat drop on forehead',
'C3':'the porpoise bows repeatedly and nervously apologizing, flippers pressed together, sweating',
'C4':'the porpoise freezes like a crashed computer, eyes spinning in swirls, smoke rising from its head, completely stiff',
'C6':'a bowl of noodles in front of the porpoise, it happily leans down and eats, cheeks puffed, very happy',
'C5':'the porpoise has a sudden realization, eyes light up, happily flaps its flippers',
'C8':'the porpoise blushes shyly, covers its face with both flippers, then peeks through them',
'C1':'the porpoise stands behind a reception desk, bows politely and smiles'}
shot=sys.argv[1]; seeds=[int(s) for s in sys.argv[2:]] or [101,202]
H='https://lightricks-ltx-video-distilled.hf.space'
import requests
c=Client('Lightricks/ltx-video-distilled', verbose=False)
for k,seed in enumerate(seeds,1):
    with open(f'{D}/portrait.png','rb') as f: p=requests.post(H+'/gradio_api/upload',files={'files':f},timeout=60).json()[0]
    prompt=A[shot]+', '+STYLE
    t=time.time()
    try:
        r=c.predict(prompt,'worst quality, inconsistent motion, blurry, jittery, distorted',p,None,1216,704,'image-to-video',5,9,seed,False,1,True,api_name='/text_to_video')
    except Exception as e:
        print(json.dumps({'shot':shot,'seed':seed,'error':str(e)[:300],'secs':round(time.time()-t,1)})); continue
    out=f'{O}/{shot}_s{k}.mp4'; shutil.copy(r[0]['video'] if isinstance(r[0],dict) else r[0], out)
    pr=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate,nb_frames:format=duration','-of','json',out]))
    s=pr['streams'][0]
    print(json.dumps({'shot':shot,'file':out.split('/')[-1],'seed':seed,'w':s['width'],'h':s['height'],'fps':s['r_frame_rate'],'dur':round(float(pr['format']['duration']),2),'secs':round(time.time()-t,1),'prompt':prompt},ensure_ascii=False))
