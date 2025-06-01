import json
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.yfinance import YFinanceTools
from agno.tools.duckduckgo import DuckDuckGoTools
from dotenv import load_dotenv
from agno.memory.v2 import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.models.google import Gemini
from agno.storage.sqlite import SqliteStorage
from agno.tools.googlesearch import GoogleSearchTools
from agno.workflow import RunEvent, RunResponse, Workflow
from agno.agent import Agent, RunResponse
from agno.models.groq import Groq
from agno.tools.googlesearch import GoogleSearchTools
from textwrap import dedent
from agno.utils.pprint import pprint_run_response
load_dotenv()


memory_db = SqliteMemoryDb(table_name="user_memory", db_file="tmp/memory.db")
storage = SqliteStorage(table_name="agent_sessions", db_file='tmp/agent.db')

memory = Memory(model=Gemini(id="gemini-2.0-flash-exp"), db=memory_db)

# we can store the memory in a sqlite database for persistence and for context of the conversation
class GPSuggestions():
    sentiment_understanding_Agent: Agent = Agent(
        name="Sentiment Understanding Agent",
        role="Analyze the sentiment of the customer",
        model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
        memory=memory,
        enable_agentic_memory=True,
        enable_user_memories=True,
        storage=storage,
        add_history_to_messages=True,
        num_history_runs=3,
        tools=[GoogleSearchTools()],
        instructions=dedent("""You are expert of understanding the interest of the customer based on its conversation with the financial advisor.
                            You will analyze the sentiment of the customer based on its conversation with the financial advisor and provide a detailed sentiment analysis, and notice all the conditions of the customer.give as much as short and to the point info that is required to understand the sentiment of the customer."""),
        expected_output=dedent("""
                                 #Sentiment Analysis
                                   
                               ##Sentiment: {What are the requirements of the customer based on its conversation with the financial advisor}
                               ##Financial Condition: {What is the financial condition of the customer based on its conversation with the financial advisor}
                               ##Customer Interest: {What is the interest of the customer based on its conversation with the financial advisor}
                               ##Surrounding Factors: {What are the surrounding factors that make this product suitable for the customer}
                               ##What Customer can afford: {What is the financial condition of the customer based on its conversation with the financial advisor}
                               ##Final Response: {final response based on the sentiment analysis of the customer}
                               """),
        markdown=True,
    )

    suggestion_agent: Agent = Agent(
        name="Product Suggestion Agent",
        role="Suggest a financial product based on the sentiment analysis",
        model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
        tools=[YFinanceTools()],
        context={"fin_products": "Financial Products like Stocks, Bonds, Mutual Funds, ETFs, etc."},
        add_context=True,
        instructions=dedent("""You are a financial advisor. Based on the sentiment analysis provided by the Sentiment Understanding Agent, suggest a financial product that aligns with the customer's interest or can help improve their financial situation."""),
        expected_output=dedent("""
                               Suggested Products:
                               ##Product Name: {product name}
                               ##Product Description: {product description}
                               ##Product Price: {product price}
                               """),
        markdown=True,
    )

    final_agent: Agent = Agent(
        name="Writer Agent",
        role="Write a final response based on the product suggestion",
        model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
        tools=[GoogleSearchTools(),YFinanceTools()],
        instructions=dedent("""You are a financial advisor. Based on the product suggestion provided by the Product Suggestion Agent, write a final response that explains the suggested financial product to the customer in a clear and concise manner."""),
        expected_output=dedent("""
                               #You Should Sell this product to the customer
                               ##Product Name: {product name}
                               ##Product Description: {product description}
                               ##Product Price: {product price}
                               ##Why this product is suitable for the customer: {reasoning for the product selection particularly based on the sentiment analysis of the customer}
                               ##What are the surrounding factors that make this product suitable for the customer: {surrounding factors that make this product suitable for the customer}
                               ##Final Response: {final response}
                               """),
        markdown=True,
        add_history_to_messages=True,
    )

    def run(self, query,user_id) -> RunResponse:
        input = query

        agent_1_response: RunResponse = self.sentiment_understanding_Agent.run(input,user_id=user_id)
        sentiment_analysis = agent_1_response.content
        agent_2_input = {
            "sentiment_analysis": sentiment_analysis,
            "query": "provide suitable financial product based on the sentiment analysis of the customer",
        }
        agent_2_response: RunResponse = self.suggestion_agent.run(json.dumps(agent_2_input,indent=4))
        product_suggestion = agent_2_response.content
        final_agent_input = {
            "product_suggestion": product_suggestion,
            "sentiment_analysis": sentiment_analysis,
            "query": "write a final response based on the product suggestion and sentiment analysis for the financial advisor to explain to the customer",
        }
        
        agent_3_response: RunResponse = self.final_agent.run(json.dumps(final_agent_input,indent=4), user_id=user_id)

        return agent_3_response.content

def run_workflow(query: str, user_id: str):
    import time
    st = time.time()
    
    generate = GPSuggestions()

    help_GP = generate.run(query,user_id)
    et = time.time()
    print(f"Time taken: {et - st} seconds")
    print(help_GP)

run_workflow("i have earnings around 10000 rupees per month and my expenses are around 8000 rupees per month. i want to invest in a financial product that can help me grow my wealth. i am interested in stocks and mutual funds. i am looking for a product that can give me good returns in the long term. i am also looking for a product that is low risk and has a good track record.", "user_123")