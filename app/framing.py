"""Local face detection for horizontal reframing of a single presenter."""
from pathlib import Path
import bisect
import av
import cv2

def face_track(video, start, end, fallback=0.5):
    detector=cv2.CascadeClassifier(str(Path(cv2.data.haarcascades)/'haarcascade_frontalface_default.xml'))
    samples=[]
    next_time=start
    with av.open(str(video)) as container:
        stream=container.streams.video[0]
        container.seek(int(start*av.time_base),backward=True)
        crop_width=stream.height*9/16
        last_center=max(0,stream.width-crop_width)*fallback+crop_width/2
        for frame in container.decode(stream):
            when=frame.time
            if when is None or when<next_time: continue
            if when>end: break
            next_time=when+0.25
            gray=frame.to_ndarray(format='gray')
            height,width=gray.shape
            factor=min(1,640/width)
            gray=cv2.resize(gray,None,fx=factor,fy=factor)
            gray=cv2.equalizeHist(gray)
            center=None
            for angle in (0,-20,20,-35,35):
                transform=cv2.getRotationMatrix2D((gray.shape[1]/2,gray.shape[0]/2),angle,1)
                rotated=cv2.warpAffine(gray,transform,(gray.shape[1],gray.shape[0])) if angle else gray
                faces=detector.detectMultiScale(rotated,scaleFactor=1.05,minNeighbors=3,minSize=(48,48))
                if len(faces):
                    x,y,w,h=max(faces,key=lambda box:box[2]*box[3])
                    inverse=cv2.invertAffineTransform(transform)
                    center=(inverse[0,0]*(x+w/2)+inverse[0,1]*(y+h/4)+inverse[0,2])/factor
                    break
            if center is not None: last_center=center
            crop_width=height*9/16
            available=width-crop_width
            position=max(0,min(1,(last_center-crop_width/2)/available)) if available>0 else fallback
            samples.append((max(0,when-start),position))
    return samples or [(0,fallback)]

def crop_commands(samples, duration):
    times=[s[0] for s in samples]
    commands=[]
    # Interpolate sampled centers to avoid discrete jumps as the speaker moves.
    for tick in range(int(duration*30)+1):
        t=tick/30
        i=bisect.bisect_right(times,t)
        if i==0: position=samples[0][1]
        elif i>=len(samples): position=samples[-1][1]
        else:
            a,x=samples[i-1];b,y=samples[i]
            position=x+(y-x)*(t-a)/(b-a)
        commands.append(f'{t:.6f} crop@follow x (iw-ow)*{position:.6f};')
    return '\n'.join(commands)
