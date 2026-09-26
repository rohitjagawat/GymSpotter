"""Optional LLM wording; local observations remain the source of the cue."""
from groq import Groq

class LLMCoach:
    def __init__(self, key='', model='openai/gpt-oss-120b'):
        self.client = Groq(api_key=key, timeout=8, max_retries=0) if key else None
        self.model = model

    def give_feedback(self, exercise, cue):
        if self.client is None:
            return cue
        try:
            response = self.client.chat.completions.create(
                model=self.model, temperature=.2, max_tokens=80,
                messages=[
                    {'role':'system','content':
                     'You are Repzy. Rephrase the supplied coaching cue in at most 20 words. '
                     'Keep its meaning. Do not add diagnoses, new observations, counts, or '
                     'exercise prescriptions. You receive heuristic text cues, not images.'},
                    {'role':'user','content':f'Exercise: {exercise}. Cue: {cue}'}])
            candidate = response.choices[0].message.content
            return candidate.strip() if candidate and len(candidate)<250 else cue
        except Exception:
            return cue
