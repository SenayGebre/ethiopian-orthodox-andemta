import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig

async def run_prompt_with_usage(prompt: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        print("Please export it in your environment or add it to .env")
        sys.exit(1)

    print(f"\n--- Sending prompt to Gemini ---")
    print(f"Prompt: {prompt}\n")

    config = LocalAgentConfig(
        api_key=api_key,
        model="gemini-3.8-flash",
        system_instructions="You are an expert AI assistant with Antigravity integration.",
        capabilities=CapabilitiesConfig(),
    )

    async with Agent(config) as agent:
        response = await agent.chat(prompt)

        # Stream response tokens
        sys.stdout.write("Response: ")
        async for token in response:
            sys.stdout.write(token)
            sys.stdout.flush()
        print("\n")

        # Track and display API token usage (#3)
        usage = agent.conversation.total_usage
        print("=" * 40)
        print("📊 GEMINI API USAGE BREAKDOWN (#3)")
        print("=" * 40)
        print(f"  • Prompt Tokens:      {usage.prompt_token_count}")
        print(f"  • Candidates Tokens:  {usage.candidates_token_count}")
        print(f"  • Thoughts Tokens:    {usage.thoughts_token_count}")
        print(f"  • Total Tokens Used:  {usage.total_token_count}")
        print("=" * 40)

if __name__ == "__main__":
    test_prompt = sys.argv[1] if len(sys.argv) > 1 else "Hello! Explain what Antigravity does in one concise paragraph."
    asyncio.run(run_prompt_with_usage(test_prompt))
