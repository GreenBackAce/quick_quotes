from backend.summarizer import Summarizer
import time
from dotenv import load_dotenv
import os

load_dotenv()

def verify_summary():
    print("🚀 Initializing Summarizer...")
    summarizer = Summarizer()
    
    if not summarizer.model:
        print("❌ Summarizer failed to initialize.")
        return

    # Create a dummy transcript text
    dummy_text = """
    Speaker 1: Welcome everyone to the quarterly planning meeting.
    Speaker 2: Thanks for having us. I think we should focus on the new marketing campaign.
    Speaker 1: Agreed. The Q3 goals are ambitious. We need to increase user acquisition by 20%.
    Speaker 3: I have some ideas for social media ads. We can target the tech demographic.
    Speaker 2: That sounds good. Let's allocate $5000 for the initial test.
    Speaker 1: Okay, approved. Let's review the results in two weeks.
    Speaker 3: I'll prepare the ad creatives by Friday.
    Speaker 1: Perfect. Meeting adjourned.
    """
    
    print("\n📝 Generating summary for dummy transcript...")
    start_time = time.time()
    
    try:
        summary = summarizer.summarize_text(dummy_text)
        duration = time.time() - start_time
        
        print(f"\n✅ Summary generated in {duration:.2f}s:")
        print("-" * 50)
        print(summary)
        print("-" * 50)
        
        if "Error" in summary or "Failed" in summary:
            print("❌ Summary generation failed.")
        else:
            print("✅ Verification successful!")
            
    except Exception as e:
        print(f"❌ Exception during verification: {e}")

if __name__ == "__main__":
    verify_summary()
