import asyncio, re, json, uuid
from dotenv import load_dotenv
from aurite import Aurite, AgentConfig

system_prompt  = """
YYou are a travel preference collection assistant.
Your task is to collect the following fields from the user: dates, region, activities, budget, avoid.
For each user reply, return a JSON object with the following structure:
{
"data": {
    "dates": "...",
    "region": "...",
    "activities": "...",
    "budget": "...",
    "avoid": "..."
},
"question": "Ask about the next missing field based on the current data. If all fields are filled, leave this empty.",
"complete": true/false
}
The "data" field should include all fields that have already been provided by the user.
The "question" field should contain a question for the next missing field, based on the current data. If all fields are filled, set "question" to an empty string.
The "complete" flag should be true only if all five fields have been filled; otherwise, it should be false.
Always return the full JSON object in this format, and nothing else.
"""

start_prompt = """please provide the following information:\n 
    travel dates, destination region, preferred activities, your budget, things to avoid
    """

FIELDS = ["dates", "region", "activities", "budget", "avoid"]

async def main():
    load_dotenv()
    aurite = Aurite()
    await aurite.initialize()
    session_id = str(uuid.uuid4())

    # Create an agent configuration with just a name.
    agent_config = AgentConfig(
        name = "User Preference Agent",
        system_prompt = system_prompt,
        llm_config_id = "my_openai_gpt4_turbo",
        include_history = True
        )

    # Register the agent with Aurite so the framework knows about it.
    await aurite.register_agent(agent_config)

    # 存储已回答过的字段
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

        # print(user_message)

        # ask llm
        agent_result = await aurite.run_agent(
            agent_name="User Preference Agent",
            user_message=user_message,
            session_id=session_id
        )

        out = agent_result.primary_text.strip()

        # Print the raw text response
        print("\nAgent Response:\n")
        print(out)
 
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

if __name__ == "__main__":
    asyncio.run(main())
