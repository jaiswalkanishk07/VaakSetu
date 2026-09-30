import asyncio
from task1_ai_core.tts import get_tts_pipeline

async def test():
    tts = get_tts_pipeline()
    try:
        res = await tts.synthesise("नमस्ते, मैं काव्या हूँ", language_code="hi-IN", speaker="kavya")
        if res:
            print("SUCCESS: Audio generated!")
        else:
            print("FAILED: No audio returned.")
    except Exception as e:
        print(f"ERROR: {e}")

asyncio.run(test())
