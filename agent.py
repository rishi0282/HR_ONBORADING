from mcp.client.session import ClientSession
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from dotenv import load_dotenv
import asyncio
import sys
import json
import os
import re
load_dotenv()
# Initialize OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Server configurations
email_server_params = StdioServerParameters(
    command=sys.executable,
    args=["email_server.py"]
)
onboarding_server_params = StdioServerParameters(
    command=sys.executable,
    args=["onboarding_server.py"]
)
# Available tools catalog
TOOLS_CATALOG = """
Available Tools:
ONBOARDING SERVER:
1. add_candidate(name, email, contact, ob_date, role, location) - Adds new candidate to Excel
2. get_candidate(employee_id) - Gets candidate information by ID
3. generate_onboarding_email_content(employee_id) - Generates onboarding email content
4. generate_training_email_content(employee_id) - Generates training email content
5. update_device_status(employee_id) - Marks device allocation as Fulfilled
6. update_ID_CARD_status(employee_id) - Marks ID card as Completed
7. update_email_setup_status(employee_id) - Marks email setup as Completed
8. update_training_status(employee_id) - Marks training as COMPLETED
9. update_training_email_status(employee_id) - Marks training email as SENT
10. update_status(employee_id, field, value) - Updates any field
11. list_all_candidates() - Lists all candidates
12. calculate_training_dates(employee_id) - Calculates training dates
EMAIL SERVER:
13. send_email(recipient_email, subject, body) - Sends single email
14. send_bulk_emails(recipients, subject, body) - Sends bulk emails (comma-separated)
"""
async def execute_tool(server_type, tool_name, arguments):
    """
    Executes a tool on the specified server.
    Args:
        server_type: 'onboarding' or 'email'
        tool_name: Name of the tool
        arguments: Dictionary of arguments
    Returns:
        Tool execution result
    """
    server_params = onboarding_server_params if server_type == 'onboarding' else email_server_params
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                name=tool_name,
                arguments=arguments
            )
            return result.content[0].text
def parse_llm_decision(llm_response):
    """
    Parses the LLM's decision and extracts action plan.
    Returns:
        List of actions to execute
    """
    try:
        # Look for JSON in the response
        json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', llm_response)
        if json_match:
            return json.loads(json_match.group())
        return None
    except:
        return None
async def intelligent_agent(user_request):
    """
    Main intelligent agent that processes user requests.
    """
    print(f"\n🤖 Agent: Processing your request...\n")
    # Step 1: Ask LLM to plan the actions
    planning_prompt = f"""
You are an HR automation agent. Analyze the user request and create an action plan.
{TOOLS_CATALOG}
User Request: "{user_request}"
IMPORTANT RULES:
1. If adding a candidate, ALL fields (name, email, contact, ob_date, role, location) are REQUIRED
2. For onboarding emails: get_candidate → generate_onboarding_email_content → send_email → update_status (OB Email and OB Email Status to "SENT")
3. For training emails: generate_training_email_content → send_email → update_status (Training Email Status to "SENT", Training Status to "IN PROGRESS")
4. For status updates: use update_status or specific update tools
5. Extract employee IDs from the request
Respond ONLY with valid JSON (no markdown, no extra text):
{{
  "action": "execute" or "ask_user" or "error",
  "message": "explanation or question to user",
  "steps": [
    {{
      "server": "onboarding" or "email",
      "tool": "tool_name",
      "arguments": {{}},
      "description": "what this does"
    }}
  ],
  "missing_fields": ["field1", "field2"] // if action is "ask_user"
}}
"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an HR automation planning agent. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": planning_prompt
                }
            ],
            temperature=0.3
        )
        llm_decision = response.choices[0].message.content.strip()
        print(f"🧠 LLM Decision:\n{llm_decision}\n")
        # Parse the decision
        plan = parse_llm_decision(llm_decision)
        if not plan:
            print("❌ Error: Could not parse LLM decision")
            return
        # Handle different actions
        if plan.get("action") == "ask_user":
            print(f"❓ {plan['message']}")
            if plan.get("missing_fields"):
                print(f"\nMissing fields: {', '.join(plan['missing_fields'])}")
            return
        elif plan.get("action") == "error":
            print(f"❌ {plan['message']}")
            return
        elif plan.get("action") == "execute":
            print(f"📋 Plan: {plan['message']}\n")
            # Execute each step
            for i, step in enumerate(plan.get("steps", []), 1):
                print(f"Step {i}: {step['description']}")
                print(f"  → Tool: {step['tool']}")
                print(f"  → Arguments: {step['arguments']}\n")
                result = await execute_tool(
                    step['server'],
                    step['tool'],
                    step['arguments']
                )
                print(f"✅ Result:\n{result}\n")
                print("-" * 60 + "\n")
            print("🎉 All tasks completed successfully!")
    except Exception as e:
        print(f"❌ Agent Error: {str(e)}")
        import traceback
        traceback.print_exc()
async def main():
    """Main agent loop"""
    print("🤖 Intelligent HR Onboarding Agent")
    print("=" * 60)
    print("\nI can help you with:")
    print("  • Adding new candidates")
    print("  • Sending onboarding emails")
    print("  • Sending training emails")
    print("  • Updating statuses (device, ID card, email, training)")
    print("  • Getting candidate information")
    print("  • Listing all candidates")
    print("\nJust tell me what you need in plain English!")
    print("=" * 60)
    while True:
        try:
            print("\n" + "=" * 60)
            user_input = input("\n👤 You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n👋 Goodbye!")
                break
            await intelligent_agent(user_input)
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
if __name__ == "__main__":
    asyncio.run(main())