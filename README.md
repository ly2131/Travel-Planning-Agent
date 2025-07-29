# Travel Planning Agent (TPA) 

---
# Part 1

This is the first part of the Travel Planning Agent (TPA) project.  
It serves as an orchestrating agent that interacts with the user, collects travel preferences, and leverages multiple tools to generate personalized destination recommendations.


## 🧩 Overview

### 🎯 Goal
To recommend a travel destination based on user preferences, real-world reviews, weather data, and estimated travel costs.

### 🧠 Core Steps

1. **Interact with the user** to gather travel preferences  
   - Example: region of interest, preferred activities, places to avoid, etc.
2. **Query the internet** based on these preferences to find high-ranking candidate destinations
3. **Retrieve weather data** for the candidate destinations
4. **Estimate budget** for visiting each destination
5. **Use an LLM** to summarize and recommend the best option to the user

---

## 🛠 Components

### 🔹 1. Preference Collection (You)
- **Function**: Conversationally gather `travel dates`, `region`, `activities`, `avoid`, and other travel-related preferences from the user.
- **LLM used**: `my_openai_gpt4_turbo`

[//]: # (- **Output example**:)

[//]: # (  ```json)

[//]: # (  {)

[//]: # (    "start_date": "2025-06-01",)

[//]: # (    "end_date": "2025-06-06",)

[//]: # (    "region": "asia",)

[//]: # (    "activities": "hiking",)

[//]: # (    "budget": "10k",)

[//]: # (    "avoid": "no")

[//]: # (  })

[//]: # (  ```)

### 🔹 2. Destination Selection (Teammate A)
- **Function**: Search internet reviews and rankings based on user input to pick top 3 recommended destinations.
- **Tool/server path**: `scrapeless-mcp-server`

[//]: # (- **Output example**: `TODO: JSON or summary of selected cities`)

### 🔹 3. Weather Information (Teammate B)
- **Function**: Get forecast for each destination (temperature, rain, etc.)
- **Tool/server path**: `Part_I_mcp_servers/weather_server.py`

[//]: # (- **Output example**: `TODO: weather JSON format`)

### 🔹 4. Price Estimation (Teammate C)
- **Function**: Estimate cost breakdown (transportation, hotel, food)
- **Tool/server path**: `Part_I_mcp_servers/city_price_server.py`,`Part_I_mcp_servers/ai_fallback_server.py`

[//]: # (- **Output example**: `TODO: budget JSON format`)

### 🔹 5. Final Recommendation
- **Function**: Combine all data and use an LLM to recommend the best travel destination
- **LLM used**: `my_openai_gpt4_turbo`
---

## 🚀 How to Run

- Run the mainCLI.py to test