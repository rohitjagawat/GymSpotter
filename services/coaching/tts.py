from io import BytesIO
from gtts import gTTS
from functools import lru_cache

class TextToSpeech:
    @lru_cache(maxsize=64)
    def speak(self, text, lang='en'):
        cleaned = (text or '').strip()
        if not cleaned:
            return None
        buffer = BytesIO()
        gTTS(text=cleaned, lang=lang, timeout=(4, 6)).write_to_fp(buffer)
        return buffer.getvalue()
