import subprocess, json, textwrap, time

class MusicPlanGenerator:
    def generate(self, context: dict) -> dict:
        prompt = self._prompt(context)

        for _ in range(3):
            try:
                raw = self._call(prompt)
                plan = json.loads(raw)
                self._validate(plan)
                return plan
            except Exception:
                time.sleep(0.2)

        raise RuntimeError("AI failed to generate valid music plan")

    def _call(self, prompt: str) -> str:
        r = subprocess.run(
            ["ollama", "run", "phi3", "--format", "json"],
            input=prompt,
            text=True,
            capture_output=True,
            check=True
        )
        return r.stdout.strip()

    def _prompt(self, context):
        return textwrap.dedent(f"""
        You are a professional video game composer.

        Generate a SYMBOLIC music plan.
        Return ONLY JSON.

        Style: dark fantasy orchestral.
        Avoid repetition. Create harmonic motion.

        Context:
        {json.dumps(context)}

        JSON SCHEMA:
        {{
          "key": "E minor",
          "tempo": 50-80,
          "sections": [
            {{
              "bars": 4,
              "chord": "Em|C|G|D",
              "energy": 0.0-1.0,
              "roles": ["bed","rhythm","accent"],
              "motif": "melancholy|heroic|null"
            }}
          ]
        }}
        """)

    def _validate(self, p):
        assert "sections" in p
        for s in p["sections"]:
            assert "chord" in s and "bars" in s
