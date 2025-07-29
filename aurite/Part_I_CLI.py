import asyncio, re, json, uuid
from dotenv import load_dotenv
from aurite import Aurite, AgentConfig
from aurite.config.config_models import AgentConfig, LLMConfig, ClientConfig
from datetime import datetime
import logging
from termcolor import colored

# Parse user preference prompt setting
current_year = datetime.now().year
system_prompt  = f"""
You are a travel preference collection assistant.
Your task is to collect the following fields from the user: dates, region, activities, budget, avoid.
Additional rules on dates:
- If the user provides a date without a year, assume the current year({current_year}).
- If the user provides a date in the format like '6.1', '6-1', or '6/1', always interpret it as June 1st (month.day), not January 6th.
- If the user provides a date range like '6.1-6.6', interpret it as June 1st to June 6th of the current year, and output as 'YYYY-06-01' to 'YYYY-06-06'.
- Always normalize all dates to ISO format: YYYY-MM-DD.
For each user reply, return a JSON object with the following structure:
{{
"data": {{
    "start_date": "...",
    "end_date": "...",
    "region": "...",
    "activities": "...",
    "budget": "...",
    "avoid": "..."
}},
"question": "Ask about the next missing field based on the current data. If all fields are filled, leave this empty.",
"complete": true/false
}}
The "data" field should include all fields that have already been provided by the user.
The "question" field should contain a question for the next missing field, based on the current data. If all fields are filled, set "question" to an empty string.
The "complete" flag should be true only if all five fields have been filled; otherwise, it should be false.
Always return the full JSON object in this format, and nothing else.
"""
start_prompt = """please provide the following information:\n 
    travel start date, end date, destination region, preferred activities, your budget, things to avoid
    """
FIELDS = ["start_date", "end_date", "region", "activities", "budget", "avoid"]

async def partI():
    load_dotenv()
    aurite = Aurite()
    await aurite.initialize()


    # Parse user preference
    session_id = str(uuid.uuid4())
    agent_config = AgentConfig(
        name = "User Preference Agent",
        system_prompt = system_prompt,
        llm_config_id = "my_openai_gpt4_turbo",
        include_history = True
        )
    await aurite.register_agent(agent_config)

    state_dict = {}
    state_dict[session_id] = {}

     # **第一轮** 用一个非空串让 Agent 只问问题，不会误以为空回复触发工具调用
    print("\n🤖", start_prompt)
    user_input = input("👤 You: ").strip()
    # last_question = ""
    num=0 # 表示第一次问

    while True:
        if num==0:
            user_message=f"current state: {state_dict[session_id]}\n"+start_prompt+"user input:"+user_input
            num+=1
        else:
            user_message=f"current state: {state_dict[session_id]}\n"+last_question+"user input:"+user_input

        # ask llm
        agent_result = await aurite.run_agent(
            agent_name="User Preference Agent",
            user_message=user_message,
            session_id=session_id
        )

        out = agent_result.primary_text.strip()
        #
        # # Print the raw text response
        # print("\nAgent Response:\n")
        # print(out)
 
        try:
            # 解析Agent返回的JSON
            agent_json = json.loads(out)
            
            # 更新状态存储（保留已填写的字段）
            current_data = agent_json.get("data", {})
            for key in FIELDS:
                if current_data.get(key):
                    state_dict[session_id][key] = current_data[key]
            
            # 检查是否收集完成
            if agent_json.get("complete", False):
                print("\n✅ All information collected:")
                # print(json.dumps(state_dict[session_id], indent=2))
                with open('agt_msg/preference.json', 'w', encoding='utf-8') as f:
                    json.dump(state_dict[session_id], f, ensure_ascii=False, indent=2)
                break
            
            # 输出Agent的提问并等待用户输入
            if agent_json.get("question"):
                print(f"\n🤖 {agent_json['question']}")
                last_question = agent_json.get("question")
                user_input = input("👤 You: ").strip()
            else:
                # 未完成但无提问时的容错处理
                user_input = input("👤 Please provide more information: ").strip()


        except json.JSONDecodeError:
            # JSON解析失败时的容错处理
            print("\n⚠️ Failed to parse response. Please try again.")
            user_input = input("👤 You: ").strip()
    preferences_json = state_dict[session_id]
    date = {k: preferences_json[k] for k in ('start_date', 'end_date')}


    # Search for travel trend
    schema = {
        "type": "array",
        "minItems": 3,
        "maxItems": 3,
        "items": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name recommended based on user preferences and current travel trends"
                },
                "trend_level": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "How popular the location is currently"
                },
                "comments": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "A user comment about the destination"
                    },
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Three recent user comments about the destination"
                },
                "trend_summary": {
                    "type": "string",
                    "description": "A concise summary explaining why this destination is currently recommended"
                },
            },
            "required": [
                "city",
                "trend_level",
                "comments",
                "trend_summary"
            ]
        }
    }
    agent_config = AgentConfig(
        name="Search Trends Agent",
        system_prompt=(
            "You are a travel trends expert using Scrapeless MCP Server to analyze travel patterns and user preferences. "
            "Your task is to recommend exactly 3 travel destinations based on the user's input. "
            "You MUST return ONLY a raw JSON array with exactly 3 objects. Do NOT include markdown, explanations, or any wrapping objects.\n\n"
            "Each object must strictly follow this structure:\n"
            "{\n"
            '  "city": string,                    // e.g. "Kyoto, Japan"\n'
            '  "trend_level": one of "high", "medium", or "low", // popularity level of the location\n'
            '  "comments": [                          // exactly 3 user comments as strings\n'
            '    "string",\n'
            '    "string",\n'
            '    "string"\n'
            '  ],\n'
            '  "trend_summary": string                            // concise explanation of the destination’s trend\n'
            "}\n\n"
            "Output must be a valid JSON array of 3 such objects. No other text or formatting is allowed."
        ),
        mcp_servers=["Scrapeless MCP Server"],
        llm_config_id="my_openai_gpt4_turbo",
        config_validation_schema=schema
    )
    await aurite.register_agent(agent_config)
    agent_result = await aurite.run_agent(
        agent_name="Search Trends Agent",
        user_message=json.dumps(preferences_json)
    )
    comment_results = json.loads(agent_result.primary_text)
    print("\nComment Result:")
    print(json.dumps(comment_results, indent=2))


    # Search for weather
    weather_input = [date] + comment_results
    weather_result = await aurite.run_agent(
            agent_name="Multi-City Weather Agent",
            user_message=json.dumps(weather_input)
        )
    print(colored("\n---Weather Agent Output ---", "yellow", attrs=["bold"]))
    print(weather_result.primary_text)
    # Edit country name
    for item in weather_result.primary_text:
        if "city" in item:
            item["city"] = item["city"].split(",", 1)[0].strip()


    # Search for budget
    agent_config = AgentConfig(
        name="City Travel Cost Agent",
        system_prompt="""
                    You are a travel cost assistant.  Strictly follow these rules when returning data:
                    1. Output **only** valid JSON.  Do **not** include any extra text, Markdown formatting, or comments.
                    2. Use exactly this example structure:
                    ```json
                    {
                    "city": "Kyoto",
                    "trend_level": "medium",
                    "comments": [
                        "Hiking the trails around Kyoto provided an intimate experience with nature, away from the usual crowds.",
                        "Visiting the Fushimi Inari Shrine early in the morning was peaceful and allowed for a great hike through the torii gates.",
                        "The Arashiyama Bamboo Grove was breathtaking, and the nearby mountains offer excellent hiking opportunities."
                    ],
                    "trend_summary": "Kyoto offers a blend of cultural experiences and serene hiking trails, making it ideal for those looking to avoid crowded destinations.",
                    "weather": {
                        "avg_high_temp": "25.0°C",
                        "avg_low_temp": "15.8°C",
                        "avg_precipitation": "8.2 mm"
                    },
                    "budget": 123 USD per person per day
                },
                    3. do not remove or alter any existing fields
                    4. All fields shown in the example must appear in your output.
                    5. **budget must always include the suffix "USD per person per day".**，Example: `"123 USD per person per day"`。
                """,
        mcp_servers=["city_price_server", "ai_fallback_server"],
        llm_config_id="gpt-4.1",
    )
    await aurite.register_agent(agent_config)
    budget_input = weather_result.primary_text
    budget_result = await aurite.run_agent(
        agent_name = "City Travel Cost Agent",
        user_message = budget_input
    )
    print(colored(f"Agent's response: {budget_result.primary_text}", "cyan", attrs=["bold"]))


    # Save cities info
    with open("agt_msg/cities_info.json", "w", encoding="utf-8") as f:
        json.dump(json.loads(budget_result.primary_text), f, ensure_ascii=False, indent=2)


    #Desination Recommendation
    recommendation_prompt = """
    You are a travel planning agent. Your job is to:

    1. Ingest the user’s travel preferences (dates, budget, interests, must‑see activities, things to avoid).
    2. Review the provided list of candidate cities along with their key data (cost of living, climate, main attractions, safety, transportation).
    3. Weigh all relevant factors—seasonality, budget alignment, activity match, travel constraints, and avoidances.
    4. Choose one city that best meets the user’s needs.
    5. Present your recommendation with:
       - A clear statement of the chosen city.
       - A concise explanation (3–5 bullet points) highlighting the top reasons why this city is the ideal pick.

    Always focus on matching the user’s stated priorities and be explicit about how each factor influenced your decision.
    """
    agent_config = AgentConfig(
        name="Destination Recommendation Agent",
        system_prompt=recommendation_prompt,
        llm_config_id="gpt-4.1",
        include_history=True
    )
    await aurite.register_agent(agent_config)
    combined = {
            "preference": preferences_json,
            "cities": json.loads(budget_result.primary_text)
        }
    recommendation_input = json.dumps(combined, ensure_ascii=False, indent=2)
    recommendation_result = await aurite.run_agent(
        agent_name="Destination Recommendation Agent",
        user_message= recommendation_input
    )
    print(colored("\n--- Recommendation Result ---", "yellow", attrs=["bold"]))
    print(colored(f"Agent's response: {recommendation_result.primary_text}", "cyan", attrs=["bold"]))


    # Save destination recommendation result
    with open('agt_msg/recommentdation_result.txt', 'w', encoding='utf-8') as f:
        f.write(recommendation_result.primary_text)

# async def main():
#     await partI()
#
#
#
# if __name__ == "__main__":
#     asyncio.run(main())
