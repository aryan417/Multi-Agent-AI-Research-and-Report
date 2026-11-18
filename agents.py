from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search,scrape_url
from dotenv import load_dotenv
load_dotenv()

#model setup
llm = ChatGroq(model="openai/gpt-oss-20b",temperature=0,max_tokens=2048)

## first agent

def build_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search]
    )

##second agent

def build_reader_agent():
    return create_agent(
        model = llm,
        tools=[scrape_url]
    )



## writer chain
writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "you are an expert reasearch writer. write clear, structured and insightful reports"),
    ("human","""write a detailed reasearch report on the topic below.
    
    Topic: {topic}
    
    Research gathered:
    {research}
    
    structure the report as:
    - introduction
    - key findings (minimum 3 well-explained points)
    - conclusion
    - sources (list all URLs found in the research)
    
    be detailed,factual and professional.""")
])


writer_chain = writer_prompt | llm | StrOutputParser()

#critic_chain
critics_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
...""")
])

critic_chain = critics_prompt | llm | StrOutputParser()