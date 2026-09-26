import hashlib, hmac, secrets, re, time, sqlite3, threading
from services.persistence.exercise_repository import connection

# OWASP scrypt minimum: N=2**17, r=8, p=1. Salt unique per password.
_HASH_LOCK = threading.Lock()
def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    with _HASH_LOCK:
        digest = hashlib.scrypt(password.encode('utf-8'), salt=bytes.fromhex(salt),
            n=131072, r=8, p=1, maxmem=256*1024*1024, dklen=32).hex()
    return f"scrypt$131072$8$1${salt}${digest}"

def verify(password, encoded):
    try:
        method,n,r,p,salt,digest = encoded.split('$')
        if (method,n,r,p) != ('scrypt','131072','8','1'):
            return False
        return hmac.compare_digest(password_hash(password, salt), encoded)
    except (ValueError, TypeError):
        return False

def validate_password(password):
    if not 4 <= len(password) <= 128:
        raise ValueError("Use a password of 4–128 characters.")
    if password.lower() in {"password123456789", "123456789012345", "abcdefghijklmnop"}:
        raise ValueError("Choose a less predictable passphrase.")

def signup(username, display_name, password):
    username = username.strip().lower()
    display_name = display_name.strip()
    if not re.fullmatch(r"[a-z0-9_]{3,24}", username):
        raise ValueError("Username: 3–24 letters, numbers or underscores.")
    if not 1 <= len(display_name) <= 50:
        raise ValueError("Enter a display name of 1–50 characters.")
    validate_password(password)
    encoded = password_hash(password)
    try:
        with connection() as c:
            c.execute("INSERT INTO accounts(username,display_name,password_hash) VALUES(?,?,?)",
                      (username,display_name,encoded))
    except sqlite3.IntegrityError:
        raise ValueError("That username is unavailable. Please choose another.") from None

def login(username, password):
    username = username.strip().lower()[:128]
    if len(password) > 128:
        return None
    with connection() as c:
        c.execute("BEGIN IMMEDIATE")
        limit = c.execute("SELECT * FROM login_limits WHERE username=?", (username,)).fetchone()
        now = time.time()
        if limit and limit['blocked_until'] > now:
            raise ValueError("Too many attempts. Try again in 15 minutes.")
        account = c.execute("SELECT * FROM accounts WHERE username=?", (username,)).fetchone()
        # Dummy hash keeps unknown-user password work comparable.
        encoded = account['password_hash'] if account else None
        okay = verify(password, encoded) if encoded else bool(password_hash(password)) and False
        if okay:
            c.execute("DELETE FROM login_limits WHERE username=?", (username,))
            return {k:account[k] for k in ('id','username','display_name')}
        failures = (limit['failures'] if limit and not limit['blocked_until'] else 0) + 1
        blocked_until = now + 900 if failures >= 5 else 0
        c.execute("INSERT OR REPLACE INTO login_limits VALUES(?,?,?)",
                  (username, failures, blocked_until))
        return None

def change_password(user_id, current, new):
    validate_password(new)
    with connection() as c:
        row = c.execute("SELECT username,password_hash FROM accounts WHERE id=?", (user_id,)).fetchone()
    if not row or not login(row['username'], current):
        raise ValueError("Current password is incorrect.")
    encoded = password_hash(new)
    with connection() as c:
        c.execute("UPDATE accounts SET password_hash=? WHERE id=?", (encoded,user_id))


import streamlit as st
from services.ui import style_loader as ui

def logout():
    if st.session_state.get('voice'): st.session_state.voice.close()
    processor=st.session_state.get('processor')
    if processor: processor.on_ended()
    for key in list(st.session_state): del st.session_state[key]
    st.rerun()


def render_login_wall():
    if st.session_state.get('account'):
        if time.time()-st.session_state.get('login_at',0)>12*3600:
            logout()
        return True
    left,right=st.columns([1.3,1],gap='large')
    with left:
        ui.brand(); st.write('')
        ui.hero('YOUR PERSONAL AI SPOTTER','SHOW UP.','LEVEL UP.',
            'Turn every session into progress. Train with live movement feedback, purposeful coaching and a clear view of your performance.')
        st.caption('01 / Choose your movement     ·     02 / Set your camera     ·     03 / Train with intent')
    with right:
        st.subheader('Your next rep starts here.')
        signin,register=st.tabs(['Sign in','Create account'])
        with signin:
            with st.form('signin'):
                username=st.text_input('Username',max_chars=24)
                password=st.text_input('Password',type='password',max_chars=128)
                submitted=st.form_submit_button('Sign in →',type='primary',width="stretch")
            if submitted:
                try:
                    account=login(username,password)
                    if account:
                        st.session_state.account=account; st.session_state.login_at=time.time()
                        st.rerun()
                    else: st.error('Username or password is incorrect.')
                except ValueError as exc: st.error(str(exc))
        with register:
            with st.form('register',clear_on_submit=True):
                name=st.text_input('Your name',max_chars=50)
                username=st.text_input('Choose a username',max_chars=24,help='3–24 letters, numbers or underscores.')
                password=st.text_input('Create a password',type='password',max_chars=128,
                    help='Use at least 4 characters.')
                confirm=st.text_input('Confirm password',type='password',max_chars=128)
                accepted=st.checkbox('I understand this is a camera-based fitness aid, not a substitute for a qualified trainer.')
                submitted=st.form_submit_button('Create my account →',type='primary',width="stretch")
            if submitted:
                try:
                    if not accepted: raise ValueError('Please acknowledge the fitness-aid notice.')
                    if password!=confirm: raise ValueError('Passwords do not match.')
                    signup(username,name,password)
                    st.success('Account created. Open Sign in to start training.')
                except ValueError as exc: st.error(str(exc))
        st.caption('Your account and workout records are stored locally. No email is required.')
    return False


