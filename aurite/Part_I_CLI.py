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

async def main():
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
                print(json.dumps(state_dict[session_id], indent=2))
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


    preferences_md = json.dumps(state_dict[session_id], indent=2)
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

    # # Search for budget
    # budget_result = await aurite.run_agent(
    #         agent_name="City Travel Cost Agent",
    #         user_message=f"Find travel budget for: {comment_results}"
    #     )
    # print(colored("\n--- Budget Result ---", "yellow", attrs=["bold"]))
    # print(colored(f"Agent's response: {budget_result.primary_text}", "cyan", attrs=["bold"]))

    #
    # Search for weather
    weather_input = comment_results.append(date)
    weather_result = await aurite.run_agent(
        agent_name="Multi-City Weather Agent",
        user_message= weather_input
    )

    # match = re.search(r"\{.*\}", weather_result.primary_text, re.DOTALL)
    # if not match:
    #     raise ValueError("No valid JSON object found in agent result.")
    # raw_data = json.loads(match.group(0))
    # print(colored("\n---Weather Agent Output ---", "yellow", attrs=["bold"]))
    # print(weather_result)





if __name__ == "__main__":
    asyncio.run(main())
