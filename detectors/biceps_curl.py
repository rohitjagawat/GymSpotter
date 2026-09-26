import math
from core.base_exercise import BaseExercise, angle, tilt

class BicepsCurlDetector(BaseExercise):
    """Track the moving arm and keep it locked throughout a repetition."""
    def __init__(self, sets=3, amount=10, rest=30):
        self.rest_seen = {}
        super().__init__('Biceps Curls (Dumbbell)', sets, amount, rest)

    def _tracking_landmarks(self, points, visibility, now):
        angles = {}
        for side, o in [('left', 0), ('right', 1)]:
            if min(visibility[i+o] for i in (11,13,15)) >= .55:
                try:
                    value = angle(points[11+o], points[13+o], points[15+o])
                except ValueError:
                    continue
                angles[side] = value
                if value >= 135:
                    self.rest_seen[side] = now
        if not self.counter.moving:
            eligible = {s:v for s,v in angles.items()
                        if now-self.rest_seen.get(s, -10000) <= 3}
            candidate = min(eligible, key=eligible.get) if eligible else None
            if candidate and (self.side not in angles or
                    angles[self.side]-angles[candidate] > 12):
                self.side = candidate
                self.counter.reset()
                self.counter.update(0, now)
                self.points = None
            elif self.side not in angles and angles:
                self.side = max(angles, key=lambda s:min(
                    visibility[i+(s=='right')] for i in (11,13,15)))
                self.counter.reset()
                self.points = None
        o = int(self.side == 'right')
        return o, [11+o,13+o,15+o], .55

    def _body_scale(self, p, o):
        return 2*math.dist(p[11+o], p[13+o])

    def _measure(self, p, o, scale):
        primary = angle(p[11+o], p[13+o], p[15+o])
        metrics = {'Elbow angle': round(primary)}
        issues = []
        if self.visibility[23+o] >= .7:
            torso = tilt(p[11+o], p[23+o])
            metrics['Torso tilt'] = round(torso)
            if angle(p[23+o], p[11+o], p[13+o]) > 25:
                issues.append('Keep your upper arm closer to your torso as you curl.')
            if torso > 18:
                issues.append('Keep your torso steady rather than leaning through the movement.')
        return primary, issues, metrics, True

    def missing(self, now, message='Keep your shoulder, elbow and wrist visible.'):
        if self.last_good is not None and 0 <= now-self.last_good <= .35:
            self.last = now
            self.latest = self._snapshot('tracking', [message], {}, False)
            return self.latest
        self.rest_seen.clear()
        return super().missing(now, message)

    def set_paused(self, value, now):
        if value != self.paused:
            self.rest_seen.clear()
        super().set_paused(value, now)

    def _finish_set(self, now):
        self.rest_seen.clear()
        super()._finish_set(now)

    def _snapshot(self, state, issues, metrics, tracked):
        snap = super()._snapshot(state, issues, metrics, tracked)
        snap['tracking_side'] = self.side or 'waiting'
        if state != 'active':
            hint = 'Keep your shoulder, elbow and wrist in view.' if state == 'tracking' else ''
        elif not self.counter.armed:
            hint = 'Lower your hand first to prepare the counter (elbow at least 135 degrees).'
        elif self.counter.moving:
            hint = 'Lower your hand again to finish the repetition.'
        else:
            hint = 'Ready: curl your hand upward, then lower it to count one rep.'
        if tracked and state == 'active' and 'Torso tilt' not in metrics:
            hint += ' Show your hip too for torso-form feedback.'
        snap['tracking_hint'] = hint
        return snap
