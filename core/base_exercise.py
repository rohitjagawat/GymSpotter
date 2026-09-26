"""Deterministic, testable 2-D movement analysis independent of Streamlit.

All points must be in pixel coordinates (same units on both axes).
These heuristics need evaluation on labelled videos before accuracy claims.
"""
import math
from collections import Counter
from services.config.workout_config import EXERCISES

def angle(a,b,c):
    u = (a[0]-b[0], a[1]-b[1]); v = (c[0]-b[0], c[1]-b[1])
    size = math.hypot(*u)*math.hypot(*v)
    if size < 1e-8:
        raise ValueError("Degenerate joint geometry")
    return math.degrees(math.acos(max(-1,min(1,(u[0]*v[0]+u[1]*v[1])/size))))

def tilt(a,b):
    return math.degrees(math.atan2(abs(a[0]-b[0]), abs(a[1]-b[1])))

class RepCounter:
    def __init__(self):
        self.reset()
    def reset(self):
        self.armed=False; self.moving=False; self.peak=0.; self.started=0.
    def update(self, progress, now):
        progress = max(0., min(1.5, progress))
        if not self.armed:
            if progress <= .15:
                self.armed=True
            return None
        if not self.moving and progress > .22:
            self.moving=True; self.started=now; self.peak=progress
        if self.moving:
            self.peak=max(self.peak,progress)
            if progress <= .15:
                duration=now-self.started
                peak=self.peak
                self.moving=False; self.peak=0.
                # Small oscillations are not reps. Shallow attempts remain visible.
                if peak >= .38 and duration >= .35:
                    return dict(full=peak>=.85, duration=round(duration,2),
                                range_percent=round(min(peak,1)*100))
        return None

class BaseExercise:
    def __init__(self, exercise, sets=3, amount=10, rest=30):
        self.exercise=exercise; self.cfg=EXERCISES[exercise]
        self.target_sets=sets; self.amount=amount; self.rest=rest
        self.counter=RepCounter(); self.points=None; self.side=None
        self.last=None; self.last_good=None; self.started=None
        self.issue_since={}; self.issue_counts=Counter(); self.previous_issues=set()
        self.reps=0; self.sets=0; self.in_set=0; self.hold=0.; self.set_hold=0.
        self.active_seconds=0.; self.records=[]; self.rep_issues=set()
        self.rest_until=0.; self.paused=False; self.pause_started=None
        self.score_samples=[]; self.last_rep=None
        self.latest=self._snapshot('ready', [], {}, False)

    @property
    def complete(self):
        return self.sets >= self.target_sets

    def set_paused(self, value, now):
        if value != self.paused:
            if value:
                self.pause_started=now
            elif self.pause_started is not None and self.rest_until:
                self.rest_until += now-self.pause_started
            self.paused=value; self.counter.reset(); self.rep_issues.clear()
            self.points=None; self.last=now; self.last_good=None

    def _snapshot(self, state, issues, metrics, tracked):
        return dict(state=state, exercise=self.exercise, tracked=tracked,
            reps=self.reps, sets=self.sets, in_set=self.in_set,
            hold_seconds=round(self.hold,1), set_hold=round(self.set_hold,1),
            active_seconds=round(self.active_seconds,1),
            score=round(sum(self.score_samples)/len(self.score_samples)) if self.score_samples else None,
            issues=issues, metrics=metrics, records=list(self.records),
            issue_counts=dict(self.issue_counts), last_rep=self.last_rep,
            rest_left=max(0,math.ceil(self.rest_until-(self.last or 0))))

    def missing(self, now, message="Step into view with the required joints visible."):
        self.last=now
        self.counter.reset(); self.rep_issues.clear(); self.issue_since.clear()
        self.previous_issues.clear(); self.points=None; self.last_good=None
        self.latest=self._snapshot('tracking', [message], {}, False)
        return self.latest

    def _finish_set(self, now):
        self.sets+=1; self.in_set=0; self.set_hold=0.
        self.counter.reset(); self.rep_issues.clear()
        self.issue_since.clear(); self.previous_issues.clear()
        self.last_good=None; self.points=None; self.side=None
        if not self.complete:
            self.rest_until=now+self.rest

    def process(self, points, visibility, now):
        dt=min(.15,max(0,now-self.last)) if self.last is not None else 0
        self.last=now
        if self.complete:
            self.latest=self._snapshot('completed', [], {}, True); return self.latest
        if self.paused:
            self.latest=self._snapshot('paused', [], {}, False); return self.latest
        if now < self.rest_until:
            self.counter.reset(); self.points=None; self.last_good=None
            self.latest=self._snapshot('rest', [], {}, False); return self.latest
        self.visibility=visibility
        offset, required, confidence = self._tracking_landmarks(points, visibility, now)
        if min(visibility[i] for i in required)<confidence:
            return self.missing(now)
        # Smooth only valid frames, reset after tracking loss to avoid ghost reps.
        if self.points is None:
            self.points=list(points)
        else:
            self.points=[(.45*p[0]+.55*q[0], .45*p[1]+.55*q[1]) for p,q in zip(points,self.points)]
        p=self.points; s,e,w,h,k,a=[i+offset for i in (11,13,15,23,25,27)]
        body_size=self._body_scale(p,offset)
        if body_size < 20:
            return self.missing(now,"Move closer so your joints can be tracked clearly.")
        shoulder_width=math.dist(p[11],p[12])/body_size
        if self.cfg['view']=='Front' and shoulder_width<.35:
            return self.missing(now,"Face the camera to assess both sides.")
        if self.cfg['view']=='Side' and not self.cfg.get('view_advisory') and shoulder_width>.95:
            return self.missing(now,"Turn side-on for this exercise's camera view.")
        try:
            primary, raw, metrics, hold_ok = self._measure(p,offset,body_size)
        except ValueError:
            return self.missing(now,"Reposition so the joints are clearly separated.")
        if self.last_good is not None:
            self.active_seconds+=dt
        self.last_good=now
        issues=[]
        for issue in raw:
            self.issue_since.setdefault(issue,now)
            if now-self.issue_since[issue]>=.65:
                issues.append(issue)
        self.issue_since={x:t for x,t in self.issue_since.items() if x in raw}
        for issue in set(issues)-self.previous_issues:
            self.issue_counts[issue]+=1
        self.previous_issues=set(issues)
        if self.cfg['kind']=='hold':
            if hold_ok:
                used=min(dt, max(0,self.amount-self.set_hold))
                self.hold+=used; self.set_hold+=used
                self.score_samples.append(max(0,100-len(issues)*15))
                if self.set_hold>=self.amount-1e-5:
                    self.records.append(dict(set=self.sets+1, seconds=self.amount,
                        score=round(sum(self.score_samples)/len(self.score_samples))))
                    self._finish_set(now)
        else:
            progress=(primary-self.cfg['start'])/(self.cfg['end']-self.cfg['start'])
            record=self.counter.update(progress,now)
            if self.counter.moving or record:
                self.rep_issues.update(issues)
            if record:
                rep_issues=set(self.rep_issues)
                if not record['full']:
                    rep_issues.add('Use a fuller comfortable range on the next rep.')
                if record['duration'] < (0.65 if self.exercise=='Jumping Jacks' else 1.2):
                    rep_issues.add('Slow down and control the next repetition.')
                self.reps+=1; self.in_set+=1
                score=max(0,100-15*len(rep_issues)-(15 if not record['full'] else 0))
                record.update(rep=self.reps,set=self.sets+1,score=score,issues=sorted(rep_issues))
                self.records.append(record); self.last_rep=record
                self.score_samples.append(score)
                for issue in rep_issues-set(issues):
                    self.issue_counts[issue]+=1
                self.rep_issues.clear()
                if self.in_set>=self.amount:
                    self._finish_set(now)
        state='completed' if self.complete else ('rest' if now<self.rest_until else 'active')
        self.latest=self._snapshot(state, issues, metrics, True)
        return self.latest

    def _tracking_landmarks(self, points, visibility, now):
        # Select a side once per set. Do not switch sides halfway through a rep.
        upper = self.exercise in ('Biceps Curls (Dumbbell)','Shoulder Press','Lateral Raises',
                    'Front Raises','Overhead Triceps Extensions','Jumping Jacks')
        left=[11,13,15,23] if upper else [11,23,25,27]
        right=[i+1 for i in left]
        if self.exercise in ('Push-ups','Plank'):
            left=[11,13,15,23,27]; right=[i+1 for i in left]
        if not self.side or (not self.counter.moving and self.last_good is None):
            self.side='left' if min(visibility[i] for i in left)>=min(visibility[i] for i in right) else 'right'
        offset=0 if self.side=='left' else 1
        required=left if offset==0 else right
        if self.cfg['view']=='Front':
            required=left+right
        if self.exercise=='Jumping Jacks':
            required+= [27,28]
        return offset, required, .7

    def _body_scale(self,p,o):
        return math.dist(p[11+o],p[23+o])

    def _measure(self,p,o,scale):
        s,e,w,h,k,a=[i+o for i in (11,13,15,23,25,27)]
        name=self.exercise; issues=[]; metrics={}; hold_ok=True
        torso=tilt(p[s],p[h])
        if name in ('Squats','Lunges','Wall Sit'):
            primary=angle(p[h],p[k],p[a]); metrics['Knee angle']=round(primary)
            # Track the visible working side; camera setup determines which leg this is.
            if torso>(45 if name=='Squats' else 25):
                issues.append('Keep your torso more upright and move with control.')
            if name=='Wall Sit':
                hold_ok=75<=primary<=110 and torso<25
                if not 75<=primary<=110:
                    issues.append('Adjust your wall-sit depth toward a right angle at the knee.')
        elif name in ('Push-ups','Plank'):
            primary=angle(p[s],p[e],p[w])
            body=angle(p[s],p[h],p[a]); metrics['Body line']=round(body)
            # Point-to-line deviation handles shoulder/ankle heights and limb proportions.
            dx=p[a][0]-p[s][0]; dy=p[a][1]-p[s][1]
            if abs(dx)<scale*.8:
                raise ValueError('Need a horizontal side view')
            line_y=p[s][1]+(p[h][0]-p[s][0])*dy/dx
            sag=(p[h][1]-line_y)/scale
            if sag>.12: issues.append('Lift your hips slightly to restore a straighter body line.')
            elif sag<-.12: issues.append('Lower your hips slightly while keeping your core engaged.')
            hold_ok=body>=155 and abs(sag)<=.18 and 55<=primary<=120 and p[h][1]<p[a][1]+scale*.5
            if name=='Plank' and not 55<=primary<=120:
                issues.append('Set your forearms down with elbows below your shoulders.')
            metrics['Elbow angle']=round(primary)
        elif name in ('Biceps Curls (Dumbbell)','Shoulder Press','Overhead Triceps Extensions'):
            primary=angle(p[s],p[e],p[w]); metrics['Elbow angle']=round(primary)
            arm=angle(p[h],p[s],p[e])
            if name=='Biceps Curls (Dumbbell)' and arm>25:
                issues.append('Keep your upper arm closer to your torso as you curl.')
            if name=='Overhead Triceps Extensions' and arm<140:
                issues.append('Keep your upper arms overhead while your elbows bend.')
            if name=='Shoulder Press':
                other=angle(p[12-o],p[14-o],p[16-o])
                if abs(primary-other)>18:
                    issues.append('Press both arms evenly; one side is moving ahead.')
                if p[w][1]>p[s][1] and primary>140:
                    issues.append('Position the weights above shoulder level before pressing.')
            if torso>18:
                issues.append('Keep your torso steady rather than leaning through the movement.')
        elif name in ('Lateral Raises','Front Raises','Jumping Jacks'):
            primary=angle(p[h],p[s],p[w]); metrics['Arm raise']=round(primary)
            if name in ('Lateral Raises','Jumping Jacks'):
                other=angle(p[24-o],p[12-o],p[16-o])
                if abs(primary-other)>18:
                    issues.append('Raise both arms together at a similar height.')
            if name!='Jumping Jacks':
                if primary>110:
                    issues.append('Keep the raise near shoulder height for this variation.')
                if angle(p[s],p[e],p[w])<135:
                    issues.append('Keep a gentle elbow bend rather than curling the weight.')
                if torso>18:
                    issues.append('Keep your torso steady rather than leaning through the movement.')
            elif primary>110 and abs(p[27][0]-p[28][0])<scale*.65:
                issues.append('Open your feet as your arms rise during the jumping jack.')
        elif name=='Standing Knee Raises':
            primary=angle(p[s],p[h],p[k]); metrics['Hip angle']=round(primary)
            if torso>20:
                issues.append('Stay tall instead of leaning back to lift your knee.')
        else:
            raise ValueError('Unsupported exercise')
        metrics['Torso tilt']=round(torso)
        return primary,issues,metrics,hold_ok
