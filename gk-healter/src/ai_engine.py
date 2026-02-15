import json
import urllib.request
import urllib.error

class AIEngine:
    def __init__(self):
        self.provider = "gemini"
        self.api_key = ""
        self.model = "gemini-2.5-flash"
        self.enabled = False

    def configure(self, provider, api_key, model="gemini-2.5-flash"):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.enabled = bool(api_key)

    def generate_insight(self, metrics, failed_services, error_count):
        if not self.enabled:
             return "AI Insights disabled. Please configure an API Key in Settings."

        try:
            prompt = self._construct_prompt(metrics, failed_services, error_count)
            if self.provider == "openai":
                return self._call_openai(prompt)
            elif self.provider == "gemini":
                return self._call_gemini(prompt)
            else:
                return "Unknown AI provider selected."
        except Exception as e:
            return f"Error gathering AI insights: {str(e)}"

    def _construct_prompt(self, metrics, failed_services, error_count):
        score = metrics.get('score', 0)
        cpu = metrics.get('cpu_percent', 0)
        mem = metrics.get('memory_percent', 0)
        disk = metrics.get('disk_percent', 0)
        failed_svc_str = ", ".join(failed_services) if failed_services else "None"
        
        prompt = (
            f"Role: Expert Linux System Administrator.\n"
            f"Task: Analyze the following periodic health report and provide a professional assessment.\n\n"
            f"--- SYSTEM METRICS ---\n"
            f"• Health Score: {score}/100\n"
            f"• CPU Load: {cpu}%\n"
            f"• RAM Usage: {mem}%\n"
            f"• Disk Usage: {disk}%\n"
            f"• Failed Units: {failed_svc_str}\n"
            f"• Journal Anomalies (24h): {error_count}\n\n"
            f"--- OUTPUT REQUIREMENTS ---\n"
            f"1. Executive Summary: A one-sentence status overview.\n"
            f"2. Critical Analysis: Identify the most pressing issue (if any).\n"
            f"3. Action Plan: Provide 3 concrete, technical steps to optimize or fix the system.\n"
            f"Format using simple headers (e.g., 'Summary:', 'Analysis:', 'Actions:'). Keep tone professional and concise."
        )
        return prompt

    def _call_openai(self, prompt):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": self.model or "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300
        }
        
        req = urllib.request.Request(url, json.dumps(data).encode('utf-8'), headers)
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content'].strip()
        except urllib.error.HTTPError as e:
            return f"OpenAI API Error: {e.code} {e.reason}"
        except Exception as e:
            return f"OpenAI Request Error: {e}"

    def _call_gemini(self, prompt):
        model_name = self.model or "gemini-2.5-flash"
        
        # API requires URL: .../models/MODEL_NAME:generateContent
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        # For Gemini, prompt is in parts > text
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        req = urllib.request.Request(url, json.dumps(data).encode('utf-8'), headers)
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                try:
                    return result['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    return "Received malformed response from Gemini."
        except urllib.error.HTTPError as e:
            return f"Gemini API Error: {e.code} {e.reason}"
        except Exception as e:
            return f"Gemini Request Error: {e}"

