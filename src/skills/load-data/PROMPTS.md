# AI & Agent Prompt Examples

This guide provides examples of how users can prompt an AI agent to use the **Load Data** skill effectively. These prompts are designed to trigger the correct sequence of discovery, safety checks, and optimized loading.

### 1. Data Exploration & Schema Discovery
> **User Prompt**: "I have a file `unknown_data.csv`. Can you tell me what columns are in there and show me the first few rows?"

- **Agent Reasoning**: The agent should call `peek_file("unknown_data.csv")` first. This provides the agent with the exact (and cleaned) column names needed to write further code.

### 2. Safeguarding Large Files
> **User Prompt**: "Analyze the distribution of price in `massive_log.csv`. Note: it's a very large file."

- **Agent Reasoning**: The agent should check the file size and use `efficient_load()`. Knowing the skill handles chunking for files > 100MB, the agent should implement a loop to process the chunk iterator returned by the skill.

### 3. DuckDB SQL Research
> **User Prompt**: "Find the top 10 most active symbols in the `daily_stats` table from my `market.db` file."

- **Agent Reasoning**: The agent should first use `peek_file("market.db")` to confirm the table names exist. It then uses `efficient_load("market.db")` to obtain a read-only connection and executes the SQL query.

### 4. Bulk Multi-file Aggregation
> **User Prompt**: "I have 100 small CSV files in `./2023_data/`. Can you merge them all and find the symbol with the highest volume?"

- **Agent Reasoning**: Instead of looping individual loads, the agent should use `collate_data(directory='./2023_data', pattern='*.csv')` to efficiently concatenate the datasets into a single DataFrame.

### 5. Cleaning Up "Dirty" Headers
> **User Prompt**: "My CSV `raw_export.csv` has messy column names with spaces and weird symbols. Load it so I can access columns easily as attributes."

- **Agent Reasoning**: The agent uses `efficient_load()`. The skill automatically sanitizes headers (e.g., `Total P/L (INR) -> total_p_l_inr`), allowing the agent to use dot-notation (`df.total_p_l_inr`) in its analysis script.
