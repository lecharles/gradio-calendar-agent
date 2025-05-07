import os
import openai
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from agents import Agent, Runner
from meeting_rescheduler.agent_tools import get_invoice_details, refund_customer, bill_customer

# Specialized agents
invoice_agent = Agent(
    name="Invoice Agent",
    instructions="You help with invoice queries.",
    tools=[get_invoice_details]
)

billing_agent = Agent(
    name="Billing Agent",
    instructions="You help with billing customers.",
    tools=[bill_customer]
)

refund_agent = Agent(
    name="Refund Agent",
    instructions="You help with customer refunds.",
    tools=[refund_customer]
)

# Orchestrator agent
orchestrator_agent = Agent(
    name="Orchestrator Agent",
    instructions=(
        "If the user asks about invoices, hand off to the Invoice Agent. "
        "If the user asks about billing, hand off to the Billing Agent. "
        "If the user asks about refunds, hand off to the Refund Agent."
    ),
    handoffs=[invoice_agent, billing_agent, refund_agent]
)

def extract_intents_entities(user_message: str):
    prompt = f'''
You are an intent and entity extraction assistant for a customer support multi-agent system.
Given the following user message, extract all intents (refund, invoice, billing) and their relevant entities (like customer_id, invoice_id, amount).
Return a JSON list of objects, each with 'intent' and 'entities' keys.

User message: "{user_message}"

Example output:
[
  {{"intent": "refund", "entities": {{"customer_id": "12345"}}}},
  {{"intent": "invoice", "entities": {{"invoice_id": "55555"}}}}
]
'''
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        temperature=0,
        max_tokens=300
    )
    import json
    return json.loads(response.choices[0].message.content)

def multi_intent_orchestrator_llm(user_message: str):
    intents = extract_intents_entities(user_message)
    responses = []
    for item in intents:
        intent = item["intent"]
        entities = item.get("entities", {})
        if intent == "refund":
            customer_id = entities.get("customer_id", "")
            if customer_id:
                responses.append(Runner.run_sync(refund_agent, f"Refund customer {customer_id}").final_output)
            else:
                responses.append("Refund intent detected, but no customer ID found.")
        elif intent == "invoice":
            invoice_id = entities.get("invoice_id", "")
            if invoice_id:
                responses.append(Runner.run_sync(invoice_agent, f"Get the invoice details for invoice {invoice_id}").final_output)
            else:
                responses.append("Invoice intent detected, but no invoice ID found.")
        elif intent == "billing":
            customer_id = entities.get("customer_id", "")
            if customer_id:
                responses.append(Runner.run_sync(billing_agent, f"Bill customer {customer_id}").final_output)
            else:
                responses.append("Billing intent detected, but no customer ID found.")
    if not responses:
        responses.append("Sorry, I couldn't identify any actionable request.")
    return "\n\n".join(responses)

def multi_intent_orchestrator(user_message: str):
    responses = []
    if "refund" in user_message.lower():
        responses.append(Runner.run_sync(refund_agent, user_message).final_output)
    if "invoice" in user_message.lower():
        responses.append(Runner.run_sync(invoice_agent, user_message).final_output)
    if "bill" in user_message.lower():
        responses.append(Runner.run_sync(billing_agent, user_message).final_output)
    if not responses:
        responses.append("Sorry, I couldn't identify any actionable request.")
    return "\n\n".join(responses)

if __name__ == "__main__":
    print("Refund example:")
    result = Runner.run_sync(orchestrator_agent, "I need to refund customer 12345")
    print(result.final_output)

    print("\nInvoice example:")
    result = Runner.run_sync(orchestrator_agent, "Get the invoice details for invoice 98765")
    print(result.final_output)

    print("\nBilling example:")
    result = Runner.run_sync(orchestrator_agent, "Bill customer 54321")
    print(result.final_output)

    print("\nHandoff example:")
    result = Runner.run_sync(orchestrator_agent, "I need a refund and also want to see my invoice for 55555")
    print(result.final_output)

    print("\nMulti-intent handoff example:")
    result = multi_intent_orchestrator("I need a refund and also want to see my invoice for 55555")
    print(result)

    print("\nLLM-based multi-intent handoff example:")
    result = multi_intent_orchestrator_llm("I need a refund for customer 12345 and also want to see my invoice for 55555")
    print(result)

