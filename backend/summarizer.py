"""
LLM-based meeting summarization using Google Gemini
"""

from typing import List, Dict, Optional
import os
import json
import config

# Try to import Google Generative AI, but handle gracefully if not available
try:
    import google.generativeai as genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    print("Warning: google-generativeai not available. Summarization will be disabled.")

import time
import random

class Summarizer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model = None

        if not GOOGLE_GENAI_AVAILABLE:
            print("Google Generative AI not available. Summarization disabled.")
            return

        if not self.api_key or self.api_key == "your-google-gemini-api-key-here":
            print("Google API key not provided or not configured. Summarization disabled.")
            return

        try:
            # Configure Gemini
            genai.configure(api_key=self.api_key)

            # Initialize the model - use stable 2.0 Flash
            self.model = genai.GenerativeModel(config.config.SUMMARY_MODEL)
            print(f"✅ Google Gemini ({config.config.SUMMARY_MODEL}) summarizer initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize Google Gemini: {e}")
            self.model = None

    def summarize_text(self, text: str) -> str:
        """
        Generate a summary from raw text with retry logic
        
        Args:
            text: The full text to summarize
            
        Returns:
            Generated summary
        """
        if not text:
            return "No text available for summarization."

        if not self.model:
            return "AI summarization not available. Please configure Google Gemini API key."

        prompt = f"""
You are an AI assistant tasked with summarizing a meeting transcript. Please provide a comprehensive yet concise summary based on the following text.

Transcript:
{text}

Please structure your summary with the following sections:
1. **Meeting Overview**: A brief description of what the meeting was about
2. **Key Discussion Points**: Main topics discussed
3. **Decisions Made**: Any decisions, agreements, or action items
4. **Next Steps**: Any follow-up actions or future plans mentioned

Keep the summary professional, objective, and focused on the most important information.
"""
        return self._generate_with_retry(prompt)

    def generate_summary(self, transcript: List[Dict]) -> str:
        """
        Generate a meeting summary from transcript list (legacy method)
        """
        if not transcript:
            return "No transcript available for summarization."
            
        formatted_transcript = self._format_transcript_for_llm(transcript)
        return self.summarize_text(formatted_transcript)

    def _generate_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Generate content with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
                else:
                    return "Failed to generate summary (empty response)."
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        print(f"⚠️  Quota exceeded. Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                
                print(f"❌ Error generating summary: {e}")
                return f"Error generating summary: {str(e)}"
        
        return "Failed to generate summary after retries due to quota limits."

    def _format_transcript_for_llm(self, transcript: List[Dict]) -> str:
        """Format transcript data for LLM consumption"""
        formatted_lines = []

        for entry in transcript:
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "").strip()

            if text:
                formatted_lines.append(f"{speaker}: {text}")

        return "\n".join(formatted_lines)

    def _create_summary_prompt(self, transcript_text: str) -> str:
        """Create the prompt for meeting summarization"""
        prompt = f"""
You are an AI assistant tasked with summarizing a meeting transcript. Please provide a comprehensive yet concise summary of the meeting based on the following transcript.

Transcript:
{transcript_text}

Please structure your summary with the following sections:
1. **Meeting Overview**: A brief description of what the meeting was about
2. **Key Discussion Points**: Main topics discussed
3. **Decisions Made**: Any decisions, agreements, or action items
4. **Next Steps**: Any follow-up actions or future plans mentioned

Keep the summary professional, objective, and focused on the most important information. If the transcript is very short or unclear, note that in your summary.

Summary:
"""

        return prompt

    def generate_action_items(self, transcript: List[Dict]) -> List[str]:
        """
        Extract action items from the meeting transcript

        Args:
            transcript: List of transcript entries

        Returns:
            List of action items
        """
        if not transcript:
            return []

        try:
            formatted_transcript = self._format_transcript_for_llm(transcript)

            prompt = f"""
Based on the following meeting transcript, extract and list all action items, tasks, or follow-up activities mentioned. Focus on:
- Specific tasks assigned to individuals
- Deadlines or timeframes mentioned
- Decisions requiring follow-up
- Next steps or future actions

Transcript:
{formatted_transcript}

Please format each action item as a clear, actionable statement. If no action items are mentioned, state "No specific action items identified."

Action Items:
"""

            response = self.model.generate_content(prompt)

            if response and response.text:
                # Parse the response into a list
                text = response.text.strip()
                if "No specific action items" in text:
                    return []

                # Split by lines and clean up
                items = [line.strip("- •").strip() for line in text.split("\n") if line.strip() and not line.lower().startswith("action items")]
                return [item for item in items if item]
            else:
                return []

        except Exception as e:
            print(f"Error extracting action items: {e}")
            return []

    def generate_key_points(self, transcript: List[Dict]) -> List[str]:
        """
        Extract key discussion points from the transcript

        Args:
            transcript: List of transcript entries

        Returns:
            List of key discussion points
        """
        if not transcript:
            return []

        try:
            formatted_transcript = self._format_transcript_for_llm(transcript)

            prompt = f"""
Analyze the following meeting transcript and extract the 5-10 most important discussion points or key takeaways. Focus on:
- Main topics discussed
- Important decisions or agreements
- Critical information shared
- Key insights or conclusions

Transcript:
{formatted_transcript}

Please list each key point as a concise bullet point.

Key Points:
"""

            response = self.model.generate_content(prompt)

            if response and response.text:
                # Parse into list
                text = response.text.strip()
                points = [line.strip("- •").strip() for line in text.split("\n") if line.strip() and not line.lower().startswith("key points")]
                return [point for point in points if point][:10]  # Limit to 10 points
            else:
                return []

        except Exception as e:
            print(f"Error extracting key points: {e}")
            return []