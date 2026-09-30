import asyncio
from task2_backend.database import list_sessions, get_agent, get_messages

async def main():
    try:
        sessions = await list_sessions()
        print("Total sessions:", len(sessions))
        for s in sessions:
            agent = await get_agent(s["agent_id"])
            messages = await get_messages(s["id"])
            print("Session ID:", s["id"], "Agent found:", bool(agent), "Message count:", len(messages))
        print("Done iterating sessions.")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
