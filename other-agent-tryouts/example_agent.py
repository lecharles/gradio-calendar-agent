from dotenv import load_dotenv
load_dotenv()

from agents import Agent, Runner, function_tool

@function_tool
def get_weather(city: str) -> str:
    """Return a haiku about the weather in a city."""
    if city.lower() == "paris":
        return (
            "Paris skies whisper\n"
            "Soft rain on old cobblestones\n"
            "Springtime memories"
        )
    return f"The weather in {city} is a poem yet to be written."

haiku_agent = Agent(
    name="Haiku Agent",
    instructions="You write haikus about cities using the weather tool.",
    tools=[get_weather]
)

if __name__ == "__main__":
    result = Runner.run_sync(haiku_agent, "Write a haiku about Paris.")
    print(result.final_output)