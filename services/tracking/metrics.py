"""Main-thread synchronization; no Streamlit state is touched by the video worker."""
import time
import streamlit as st
from services.persistence.exercise_repository import save_workout
from services.auth.login_wall import logout
from services.coaching.voice_pipeline import reset_voice
from services.ui import style_loader as ui

def persist(snapshot,status):
    save_workout(st.session_state.account['id'],st.session_state.workout_id,
                 st.session_state.exercise,st.session_state.plan,snapshot,status)


def finish_workout(status='ended'):
    processor=st.session_state.get('processor')
    snap=processor.snapshot() if processor else st.session_state.last_snapshot
    if snap:
        persist(snap,status)
        st.session_state.finished=snap
    if processor:
        processor.pause(True)
        processor.on_ended()
    st.session_state.active=False; st.session_state.paused=False
    st.session_state.processor=None
    reset_voice()
    st.session_state.voice_event=dict(id='finished-'+str(st.session_state.workout_id),
        exercise=st.session_state.exercise, cue='Session saved. Good work. Take a moment to recover.',
        expires=time.monotonic()+25)
    st.rerun()


@st.fragment(run_every=.5)
def live_panel(context):
    if time.time()-st.session_state.get('login_at',0)>12*3600:
        logout()
    processor=context.video_processor
    if processor is None:
        st.session_state.pop('voice_event',None)
        st.info('Start your camera above. Allow camera access when your browser asks.'); return
    st.session_state.processor=processor
    if processor.ended:
        st.session_state.pop('voice_event',None)
        st.warning('The camera stopped. Save this session and start a new workout to reconnect.'); return
    processor.pause(st.session_state.paused)
    snap=processor.snapshot(); st.session_state.last_snapshot=snap
    st.caption(f"Pose model: {'ready' if snap.get('model_ready') else 'not loaded'} � Camera frames received: {snap.get('frames_received', 0)}")
    if snap.get('error'):
        st.error(snap['error'])
        st.session_state.pop('voice_event',None)
        return
    if time.monotonic()-st.session_state.last_save>2:
        persist(snap,'completed' if snap['state']=='completed' else 'active')
        st.session_state.last_save=time.monotonic()
    if snap['state']=='completed':
        finish_workout('completed')
    plan=st.session_state.plan
    a,b,c,d=st.columns(4)
    if plan['kind']=='hold':
        a.metric('Total hold',f"{snap['hold_seconds']:.1f}s")
        b.metric('This hold',f"{snap['set_hold']:.1f} / {plan['amount']}s")
    else:
        a.metric('Total reps',snap['reps'])
        b.metric('This set',f"{snap['in_set']} / {plan['amount']}")
    c.metric('Sets complete',f"{snap['sets']} / {plan['sets']}")
    d.metric('Session form',f"{snap['score']} / 100" if snap['score'] is not None else '—')
    total=plan['sets']*plan['amount']
    st.progress(min(1.,(snap['hold_seconds'] if plan['kind']=='hold' else snap['reps'])/total))
    rep_number=(snap.get('last_rep') or {}).get('rep')
    if rep_number is not None and rep_number!=st.session_state.get('last_rep_cue_number'):
        st.session_state.last_rep_cue_number=rep_number
        st.session_state.last_rep_cue_at=time.monotonic()
    if snap['state']=='rest':
        cue=f"Set complete. Rest for {snap['rest_left']} seconds."
        st.info(cue)
    elif st.session_state.paused:
        cue='Workout paused. Resume when you are ready.'; st.info(cue)
    elif snap['issues']:
        cue=snap['issues'][0]
    elif (snap.get('last_rep') and snap['last_rep'].get('issues')
          and time.monotonic()-st.session_state.get('last_rep_cue_at',0)<6):
        cue=snap['last_rep']['issues'][0]
    elif snap['tracked']:
        cue='Keep your movement controlled. Complete your comfortable range.'
    else:
        cue='Find your starting position with the required joints visible.'
    ui.coach(cue)
    spoken_cue = 'Set complete. Take your rest before the next set.' if snap['state']=='rest' else cue
    event_id = (st.session_state.workout_id, snap['state'], snap['sets'], spoken_cue)
    if not st.session_state.paused:
        st.session_state.voice_event=dict(id=event_id,exercise=st.session_state.exercise,
            cue=spoken_cue,expires=time.monotonic()+3)
    else:
        st.session_state.pop('voice_event',None)
    if snap.get('tracking_hint'):
        st.info(snap['tracking_hint'])
        st.caption('Tracked arm: '+snap.get('tracking_side','waiting').title())
    if snap['metrics']:
        st.caption('  ·  '.join(f'{key}: {value}°' for key,value in snap['metrics'].items()))
    st.caption('Tracking: '+('visible joints' if snap['tracked'] else 'waiting')+' · '+snap['state'].title())
    with st.expander('Latest rep details'):
        if snap.get('last_rep'):
            r=snap['last_rep']; st.write(f"Rep {r['rep']} · {r['duration']}s movement · {r['range_percent']}% target range · {r['score']}/100")
            for issue in r['issues']: st.write('• '+issue)
        else: st.caption('Complete one repetition to see its breakdown.')


