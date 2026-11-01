import argparse
import asyncio
import json
import uuid
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from src.agent import HelpdeskAgent
from src.config import Settings


async def main():
    parser = argparse.ArgumentParser(description="Synthetic Campus Helpdesk - scenario 23")
    parser.add_argument("--user", default="student")
    parser.add_argument("--session", default=None)
    parser.add_argument("--message", help="Run one turn and exit; new process starts with no chat history.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    session = args.session or uuid.uuid4().hex[:12]
    agent = HelpdeskAgent(Settings())

    async def turn(text):
        result = await agent.run(text, args.user, session)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["answer"])
        if not args.json:
            for draft in result.get("pending_tickets", []):
                print(f'Pending draft {draft["id"]}: {draft["summary"]}\nConfirm: /confirm {draft["id"]}')
            if result["sources"]:
                print("Sources:", ", ".join(s["citation"] for s in result["sources"]))

    if args.message:
        await turn(args.message)
        return
    print(f"Campus Helpdesk | SIMULATED data | user={args.user} | session={session}")
    print("Type /new for a new session, /memory for saved facts, /quit to exit. Do not enter secrets.")
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text == "/quit":
            break
        if text == "/new":
            session = uuid.uuid4().hex[:12]
            print("New session:", session)
        elif text == "/memory":
            print(json.dumps(agent.store.facts(args.user), indent=2))
        elif text:
            await turn(text)


if __name__ == "__main__":
    asyncio.run(main())
