import threading, time, copy
import av, cv2, mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from streamlit_webrtc import VideoProcessorBase
from services.config.workout_config import MODEL, CONNECTIONS
from detectors import create_detector

class VideoProcessorClass(VideoProcessorBase):
    def __init__(self, exercise, plan):
        self.lock=threading.RLock()
        self.engine=create_detector(exercise,plan['sets'],plan['amount'],plan['rest'])
        self.error=None; self.last_frame=0.; self.timestamp=0
        self.model=None; self.ended=False
        try:
            self.model=vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(MODEL)),
                running_mode=vision.RunningMode.VIDEO, num_poses=1,
                min_pose_detection_confidence=.7,min_pose_presence_confidence=.7,
                min_tracking_confidence=.7))
        except Exception:
            self.error='Pose model could not load. Check ml_models/pose_landmarker_full.task.'

    def snapshot(self):
        with self.lock:
            result=copy.deepcopy(self.engine.latest)
            if self.error: result['error']=self.error
            if self.last_frame and time.monotonic()-self.last_frame>2 and result['state'] not in ('completed','paused','rest'):
                result.update(tracked=False,state='tracking',issues=['Camera frames stopped. Reconnect the camera.'])
            return result

    def pause(self,value):
        with self.lock:
            self.engine.set_paused(value,time.monotonic())

    def recv(self,frame):
        img=frame.to_ndarray(format='bgr24')
        with self.lock:
            now=time.monotonic(); self.last_frame=now
            if self.model is None:
                cv2.putText(img,self.error or 'Camera stopped',(15,35),cv2.FONT_HERSHEY_SIMPLEX,.55,(80,100,255),1)
                return av.VideoFrame.from_ndarray(img,format='bgr24')
            self.timestamp=max(self.timestamp+1,int(now*1000))
            try:
                result=self.model.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(img,cv2.COLOR_BGR2RGB)), self.timestamp)
                if result.pose_landmarks:
                    lm=result.pose_landmarks[0]; height,width=img.shape[:2]
                    points=[(x.x*width,x.y*height) for x in lm]
                    snap=self.engine.process(points,[x.visibility for x in lm],now)
                    color=(195,190,185) if not snap['issues'] else (69,122,240)
                    for a,b in CONNECTIONS:
                        if lm[a].visibility>=.7 and lm[b].visibility>=.7:
                            cv2.line(img,tuple(map(int,points[a])),tuple(map(int,points[b])),color,3,cv2.LINE_AA)
                    for i in {j for edge in CONNECTIONS for j in edge}:
                        if lm[i].visibility>=.7:
                            cv2.circle(img,tuple(map(int,points[i])),5,(240,245,245),-1,cv2.LINE_AA)
                else:
                    # Let rest / pause / completion continue without pose acquisition.
                    if self.engine.complete or self.engine.paused or now<self.engine.rest_until:
                        snap=self.engine.process([(0,0)]*33,[0]*33,now)
                    else:
                        snap=self.engine.missing(now)
                cv2.rectangle(img,(0,0),(img.shape[1],48),(20,24,23),-1)
                label=f"GYMSPOTTER  |  {snap['state'].upper()}  |  REPS {snap['reps']}"
                cv2.putText(img,label,(16,31),cv2.FONT_HERSHEY_SIMPLEX,.6,(69,122,240),2,cv2.LINE_AA)
            except Exception:
                self.engine.missing(now,'Tracking interrupted. Stop and restart the camera.')
                self.error='Pose processing failed. Stop and restart this workout.'
        return av.VideoFrame.from_ndarray(img,format='bgr24')

    def on_ended(self):
        with self.lock:
            if self.model:
                self.model.close(); self.model=None
            self.ended=True
