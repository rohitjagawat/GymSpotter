"""Repzy — run with: python -m streamlit run main.py"""
from functools import partial
import json, uuid
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.config.workout_config import ROOT, EXERCISES, MODEL, get_setting as setting
from services.persistence.exercise_repository import init_db, history
from services.auth.login_wall import render_login_wall, change_password, logout
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import live_panel, finish_workout
from services.state.session_default import initial_session_defaults
from services.ui import style_loader as ui
from services.coaching.voice_pipeline import voice_output, reset_voice

load_dotenv(ROOT/'.env')

def start_workout(exercise,sets,amount,rest):
    reset_voice()
    st.session_state.pop('last_rep_cue_number',None)
    st.session_state.pop('last_rep_cue_at',None)
    st.session_state.exercise=exercise
    st.session_state.plan=dict(sets=int(sets),amount=int(amount),rest=int(rest),kind=EXERCISES[exercise]['kind'])
    st.session_state.workout_id=uuid.uuid4().hex
    st.session_state.active=True; st.session_state.paused=False
    st.session_state.last_save=0.; st.session_state.last_snapshot={}
    st.session_state.processor=None
    st.rerun()

def library():
    st.title('THE MOVEMENT LIBRARY')
    st.caption('Choose the right view. Give every repetition your full attention.')
    group=st.selectbox('Filter by focus',['All','Upper body','Lower body','Core','Conditioning'])
    selected=[(n,c) for n,c in EXERCISES.items() if group=='All' or c['group']==group]
    for row in range(0,len(selected),3):
        columns=st.columns(3)
        for j,(name,cfg) in enumerate(selected[row:row+3]):
            with columns[j]:
                ui.exercise_card(row+j+1,name,cfg)
                st.caption(cfg['cue'])
                if st.button('Train this movement →',key='lib_'+name,width="stretch"):
                    st.session_state.exercise=name; st.session_state.page='Train'; st.rerun()
    st.info('Use the specified camera view. Single-leg movements track one visible side per set; switch sides between sets. The camera does not verify equipment, wall contact or load.')

def overview():
    user=st.session_state.account
    ui.hero('WELCOME BACK, '+user['display_name'],'TRAIN WITH','INTENT.',
        'Your next stronger session starts here. Find your movement, dial in your form and build a record you can grow from.')
    rows=history(user['id'])
    a,b,c,d=st.columns(4)
    a.metric('Saved sessions',len(rows)); b.metric('Total repetitions',sum(r['reps'] for r in rows))
    c.metric('Tracked minutes',round(sum(r['active_seconds'] for r in rows)/60))
    d.metric('Exercises explored',len({r['exercise'] for r in rows}))
    st.write('')
    left,right=st.columns([1.6,1],gap='large')
    with left:
        st.subheader('Make your next set count.')
        ui.camera_empty()
        if st.button('Enter training studio →',type='primary',width="stretch"):
            st.session_state.page='Train'; st.rerun()
    with right:
        st.subheader('The Repzy approach')
        ui.coach('One clear cue at a time. Refine the next repetition instead of chasing a perfect score.')
        st.markdown('**01 · Frame your movement**  \nChoose a front or side view with enough room to see the required joints.')
        st.markdown('**02 · Train with control**  \nWatch your range, symmetry and movement tempo.')
        st.markdown('**03 · Build your record**  \nReview sessions, repetitions and recurring cues in Progress.')
    st.caption('Form scores are experimental rule-based indicators. They are not medical assessments or a guarantee of safe technique.')

def train():
    st.title('THE TRAINING STUDIO')
    st.caption('Better movement. One repetition at a time.')
    if not st.session_state.active:
        if 'finished' in st.session_state:
            snap=st.session_state.pop('finished')
            st.success(f"Session saved · {snap.get('reps',0)} reps · {snap.get('sets',0)} completed sets · {snap.get('hold_seconds',0)}s hold time")
        left,right=st.columns([1.5,1],gap='large')
        with right:
            names=list(EXERCISES)
            exercise=st.selectbox('Exercise',names,index=names.index(st.session_state.exercise))
            cfg=EXERCISES[exercise]
            sets=st.number_input('Sets',min_value=1,max_value=10,value=3)
            amount=st.number_input('Seconds per hold' if cfg['kind']=='hold' else 'Reps per set',
                min_value=5 if cfg['kind']=='hold' else 1,max_value=180 if cfg['kind']=='hold' else 50,
                value=30 if cfg['kind']=='hold' else 10,key='amount_'+cfg['kind'])
            rest=st.slider('Rest between sets (seconds)',0,120,30,5)
            st.toggle('Spoken coaching',key='voice_enabled',on_change=reset_voice,
                help='Speak concise form cues through your browser. Use Test voice below to check sound before training.')
            if not MODEL.exists(): st.error('Missing pose model. See README setup instructions.')
            if st.button('Start workout →',type='primary',width="stretch",disabled=not MODEL.exists()):
                start_workout(exercise,sets,amount,rest)
        with left:
            ui.camera_empty(); ui.coach(cfg['cue'])
            st.caption(f"{cfg['view']} view · {cfg['checks']}")
            st.info('Start in the resting position. Complete the full outward-and-return movement to register a rep. Keep only one person in view.')
    else:
        name=st.session_state.exercise; plan=st.session_state.plan
        st.subheader(name)
        ui.coach(EXERCISES[name]['cue'])
        a,b,c=st.columns([1,1,2])
        with a:
            if st.button('Resume' if st.session_state.paused else 'Pause',width="stretch"):
                reset_voice()
                st.session_state.paused=not st.session_state.paused
                if st.session_state.get('processor'): st.session_state.processor.pause(st.session_state.paused)
        with b:
            if st.button('End & save',width="stretch"): finish_workout()
        with c: st.toggle('Spoken coaching',key='voice_enabled',on_change=reset_voice)
        rtc={'iceServers':[{'urls':['stun:stun.l.google.com:19302']}]}
        configured=setting('RTC_CONFIGURATION')
        if configured:
            try: rtc=json.loads(configured)
            except json.JSONDecodeError: st.error('RTC_CONFIGURATION must be valid JSON.')
        context=webrtc_streamer(key='camera_'+st.session_state.workout_id,mode=WebRtcMode.SENDRECV,
            video_processor_factory=partial(VideoProcessorClass,name,plan),
            rtc_configuration=rtc,
            media_stream_constraints={'video':{'width':{'ideal':960},'height':{'ideal':540},'frameRate':{'ideal':24,'max':30}},'audio':False},
            async_processing=True,video_html_attrs={'autoPlay':True,'controls':False,'muted':True,'style':{'width':'100%','borderRadius':'14px'}})
        live_panel(context)
        st.caption('Only valid, visible tracking contributes to hold time. Pause or end the workout before leaving this screen.')
    voice_output()

def progress():
    st.title('PROGRESS, MADE VISIBLE')
    rows=history(st.session_state.account['id'])
    if not rows:
        st.info('Your first saved workout starts your progress story.'); return
    df=pd.DataFrame(rows)
    df['date']=pd.to_datetime(df['created_at']).dt.date
    a,b,c=st.columns(3)
    a.metric('Total reps',int(df['reps'].sum())); b.metric('Completed sets',int(df['sets'].sum()))
    c.metric('Tracked minutes',round(df['active_seconds'].sum()/60,1))
    st.subheader('Your daily training volume')
    daily=df.groupby('date')[['reps']].sum(); st.bar_chart(daily,color='#f07a45')
    st.subheader('Session journal')
    columns=['created_at','exercise','reps','sets','hold_seconds','score','status']
    st.dataframe(df[columns],hide_index=True,width="stretch")
    st.caption('An active record is an autosaved session that may have been interrupted. Timestamps use UTC. Scores are experimental and are not comparable across different exercises.')
    export=df[columns].copy()
    st.download_button('Export my history (CSV)',export.to_csv(index=False).encode('utf-8'),
        file_name='repzy-history.csv',mime='text/csv')
    selection=st.selectbox('Review a session',range(len(rows)),
        format_func=lambda i:f"{rows[i]['created_at']} — {rows[i]['exercise']} — {rows[i]['id'][:6]}")
    details=json.loads(rows[selection]['details'])
    if details.get('records'):
        st.dataframe(pd.DataFrame(details['records']),hide_index=True,width="stretch")
    if details.get('issues'):
        st.subheader('Cues recorded in this session')
        for issue,count in details['issues'].items(): st.write(f'{count} × {issue}')

def account():
    st.title('YOUR ACCOUNT')
    st.write('Signed in as **'+st.session_state.account['username']+'**')
    with st.form('change_password',clear_on_submit=True):
        st.subheader('Change password')
        current=st.text_input('Current password',type='password',max_chars=128)
        new=st.text_input('New password (at least 4 characters)',type='password',max_chars=128)
        confirm=st.text_input('Confirm new password',type='password',max_chars=128)
        submit=st.form_submit_button('Update password',type='primary')
    if submit:
        try:
            if new!=confirm: raise ValueError('Passwords do not match.')
            change_password(st.session_state.account['id'],current,new)
            st.success('Password updated.')
        except ValueError as exc: st.error(str(exc))
    st.subheader('Your data & camera')
    st.write('Video is processed by the Python server. Frames are not saved by this app. Workout metrics are saved locally in SQLite. If you host the app remotely, video travels to that server over WebRTC.')
    st.write('With spoken coaching enabled, text is sent to Google TTS; with a Groq key, exercise names and text cues are also sent to Groq. No camera frames are sent to either service by this app.')
    st.caption('Password-protected accounts use new tables in your existing data.db. Legacy username-only accounts and history remain stored, but are not linked automatically.')

def main():
    st.set_page_config(page_title='Repzy · Your Personal AI Spotter',page_icon='🏋️',layout='wide')
    ui.theme(); init_db()
    if not render_login_wall(): return
    initial_session_defaults()
    with st.sidebar:
        ui.brand(); st.caption('YOUR PERSONAL AI SPOTTER'); st.divider()
        st.write('Welcome, '+st.session_state.account['display_name'])
        pages=['Overview','Train','Exercise library','Progress','Account']
        for page in pages:
            if st.button(page,key='nav_'+page,type='primary' if st.session_state.page==page else 'secondary',
                         width="stretch",disabled=st.session_state.active and page!='Train'):
                if page!='Train': reset_voice()
                st.session_state.page=page; st.rerun()
        st.divider()
        st.caption('12 movements. One stronger you.')
        st.caption('End your workout before signing out.' if st.session_state.active else 'Move well. Build consistently.')
        if st.button('Sign out',disabled=st.session_state.active,width="stretch"): logout()
    {'Overview':overview,'Train':train,'Exercise library':library,'Progress':progress,'Account':account}[st.session_state.page]()

if __name__=='__main__': main()
