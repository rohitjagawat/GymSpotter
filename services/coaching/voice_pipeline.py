"""Latest-cue speech generation with playback outside the metrics fragment."""
from concurrent.futures import ThreadPoolExecutor
import time
import uuid
import streamlit as st
from services.coaching.tts import TextToSpeech
from services.coaching.llm import LLMCoach


class VoicePipeline:
    def __init__(self, key='', model='openai/gpt-oss-120b', tts=None, clock=time.monotonic):
        self.llm = LLMCoach(key, model)
        self.tts = tts or TextToSpeech()
        self.clock = clock
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='gymspotter-voice')
        self.future = None
        self.pending = None
        self.desired = None
        self.generation = 0
        self.closed = False
        self.next_allowed = 0.
        self.delivered = None

    def reset(self):
        """Invalidate in-flight audio without queueing another network request."""
        self.generation += 1
        self.desired = None
        self.delivered = None
        self.next_allowed = 0.
        if self.future is not None and self.future.cancel():
            self.future = None
            self.pending = None

    def request(self, exercise, cue, event_id=None, force=False, rewrite=False):
        identity = event_id or (exercise, cue)
        self.desired = identity
        if self.closed or not cue or self.future is not None:
            return False
        now = self.clock()
        if not force and (identity == self.delivered or now < self.next_allowed):
            return False
        self.pending = (identity, self.generation, now)
        self.future = self.pool.submit(self._make, exercise, cue, rewrite)
        return True

    def _make(self, exercise, cue, rewrite):
        # Corrections bypass the LLM: no extra latency or reinterpreted observations.
        text = self.llm.give_feedback(exercise, cue) if rewrite else cue
        try:
            audio = self.tts.speak(text)
            if not audio:
                raise ValueError('Empty speech response')
            return text, audio, None
        except Exception:
            return text, None, 'Speech service unavailable. Check your internet connection and try Test voice. Text coaching still works.'

    def poll(self):
        if self.future is None or not self.future.done():
            return None
        future, pending = self.future, self.pending
        self.future = None
        self.pending = None
        identity, generation, requested_at = pending
        now = self.clock()
        if generation != self.generation or identity != self.desired or now-requested_at > 15:
            return None
        text, audio, error = future.result()
        if error:
            self.next_allowed = now + 20
        else:
            self.delivered = identity
            self.next_allowed = now + max(7, len(text.split()) / 2.0 + 2)
        return text, audio, error

    def close(self):
        self.reset()
        self.closed = True
        self.pool.shutdown(wait=False, cancel_futures=True)


def reset_voice():
    voice = st.session_state.get('voice')
    if voice is not None:
        if hasattr(voice, 'reset'):
            voice.reset()
        else:
            voice.close()
            del st.session_state['voice']
    for key in ('voice_audio', 'voice_test_event', 'voice_error', 'voice_text', 'voice_event'):
        st.session_state.pop(key, None)


def playback_bytes(audio):
    """A valid ID3v1 title gives cached MP3s a fresh media identity for replay."""
    title = uuid.uuid4().hex[:30].encode('ascii')
    return audio + b'TAG' + title.ljust(30, b'\x00') + b'\x00' * 95


def voice_output():
    """Voice refreshes independently of the camera's changing metrics layout."""
    with st.container(border=True):
        st.markdown('**COACH AUDIO**')
        voice_controls()


@st.fragment(run_every=.5)
def voice_controls():
    enabled = st.session_state.get('voice_enabled', False)
    paused = st.session_state.get('paused', False)
    if not enabled or paused:
        if st.session_state.pop('voice_running', False):
            reset_voice()
        st.caption('Coaching muted. Enable Spoken coaching above.' if not enabled else 'Audio paused with your workout.')
        return

    from services.config.workout_config import get_setting
    voice = st.session_state.get('voice')
    if voice is None or not hasattr(voice, 'reset'):
        if voice is not None:
            voice.close()
        voice = VoicePipeline(get_setting('GROQ_API_KEY'), get_setting('GROQ_MODEL', 'openai/gpt-oss-120b'))
        st.session_state.voice = voice
    st.session_state.voice_running = True

    if st.button('Test voice', key='test_voice', help='Play a short sample before you begin your workout.'):
        voice.reset()
        st.session_state.voice_error = None
        st.session_state.voice_test_event = {
            'id': 'test-' + uuid.uuid4().hex,
            'cue': 'GymSpotter voice check. I am ready to coach your next set.',
            'exercise': '', 'expires': time.monotonic() + 20, 'force': True,
        }

    now = time.monotonic()
    test = st.session_state.get('voice_test_event')
    if test and test['expires'] < now:
        st.session_state.pop('voice_test_event', None)
        test = None
    event = test or st.session_state.get('voice_event')
    if event and event.get('expires', 0) >= now:
        voice.request(event.get('exercise', ''), event['cue'], event_id=event['id'],
                      force=bool(test) and voice.delivered != event['id'])
    else:
        voice.desired = None

    result = voice.poll()
    if result:
        text, audio, error = result
        st.session_state.voice_text = text
        st.session_state.voice_error = error
        if audio:
            data = playback_bytes(audio)
            st.session_state.voice_audio = data
        if test:
            st.session_state.pop('voice_test_event', None)

    # Render the SAME media bytes in the SAME position on every fragment run.
    # Streamlit/React keeps the player mounted; omission would stop it after 0.5s.
    with st.container(key='persistent_voice_player'):
        cached = st.session_state.get('voice_audio')
        if cached:
            st.audio(cached, format='audio/mp3', autoplay=True)

    if st.session_state.get('voice_error'):
        st.warning(st.session_state.voice_error)
    elif voice.future is not None:
        st.caption('Preparing your coaching cue…')
    elif st.session_state.get('voice_text'):
        st.caption(st.session_state.voice_text)
    else:
        st.caption('Test your sound before starting. Coaching uses your browser’s audio output.')
    st.caption('If your browser blocks autoplay, press ▶ on the player. Keep this tab unmuted.')
