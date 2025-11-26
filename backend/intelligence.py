"""
Meeting Intelligence module for Quick Quotes Quill
Handles "Chat with Meeting" (RAG) and "Meeting Analytics" features.
"""

from typing import List, Dict, Any, Optional
import google.generativeai as genai
import config
import collections

class MeetingIntelligence:
    def __init__(self):
        self.api_key = config.config.GOOGLE_API_KEY
        self.model = None
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(config.config.SUMMARY_MODEL)
                print(f"✅ Intelligence module initialized with {config.config.SUMMARY_MODEL}")
            except Exception as e:
                print(f"❌ Failed to initialize Intelligence module: {e}")
        else:
            print("⚠️ Google API Key not found. Intelligence features disabled.")

    def chat_with_meeting(self, transcript: List[Dict], question: str) -> str:
        """
        Answer a user question based on the meeting transcript (RAG).
        """
        if not self.model:
            return "AI features are not available (API Key missing)."
        
        if not transcript:
            return "No transcript available to answer questions."

        # 1. Prepare Context (Simple RAG: Dump whole transcript for now)
        # For very long meetings, we might need chunking, but Gemini 1.5/2.0 has huge context.
        context = self._format_transcript(transcript)
        
        # 2. Construct Prompt
        prompt = f"""
You are a helpful assistant answering questions about a meeting.
Use the following meeting transcript as your ONLY source of information.
If the answer is not in the transcript, say "I couldn't find that information in the meeting."

TRANSCRIPT:
{context}

USER QUESTION: "{question}"

ANSWER:
"""
        # 3. Generate Answer
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error in chat_with_meeting: {e}")
            return "Sorry, I encountered an error while processing your question."

    def analyze_meeting(self, transcript: List[Dict]) -> Dict[str, Any]:
        """
        Generate analytics for the meeting: Talk time, Sentiment, Topics.
        """
        if not transcript:
            return {}

        analytics = {
            "talk_time": self._calculate_talk_time(transcript),
            "sentiment": self._analyze_sentiment(transcript),
            # "topics": self._extract_topics(transcript) # Can add later
        }
        return analytics

    def _calculate_talk_time(self, transcript: List[Dict]) -> Dict[str, float]:
        """
        Calculate total speaking time per speaker in seconds.
        """
        talk_time = collections.defaultdict(float)
        
        for entry in transcript:
            speaker = entry.get("speaker", "Unknown")
            start = entry.get("start", 0)
            end = entry.get("end", 0)
            duration = end - start
            
            if duration > 0:
                talk_time[speaker] += duration
                
        return dict(talk_time)

    def _analyze_sentiment(self, transcript: List[Dict]) -> Dict[str, Any]:
        """
        Analyze the overall sentiment of the meeting using LLM.
        """
        if not self.model:
            return {"overall": "Unknown", "score": 0.0}

        context = self._format_transcript(transcript)
        
        prompt = f"""
Analyze the sentiment of this meeting transcript.
Return a valid JSON object with the following keys:
- "overall": One of ["Positive", "Neutral", "Negative", "Tense", "Productive"]
- "score": A float between -1.0 (Negative) and 1.0 (Positive)
- "explanation": A brief 1-sentence explanation.

TRANSCRIPT:
{context[:10000]} ... (truncated if too long)
"""
        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            import json
            return json.loads(response.text)
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return {"overall": "Error", "score": 0.0}

    def _format_transcript(self, transcript: List[Dict]) -> str:
        """Convert transcript list to string format."""
        lines = []
        for entry in transcript:
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "")
            lines.append(f"{speaker}: {text}")
        return "\n".join(lines)
