from agents import build_reader_agent,build_search_agent,writer_chain,critic_chain


def run_search_pipeline(topic : str) -> dict:
    state = {}
    
    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages":[("user",f"find recent,realiable and detailed information about: {topic}")]
    }) 
    state["search_results"] = search_result['messages'][-1].content
    print("\n search result",state["search_results"])


    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages":[("user",
                     f"based on the following search results about {topic}"
                     f"pick the most relevant URL and scrape it for deeper content.\n\n"
                     f"search results:\n{state['search_results'][:4000]}")]
    })
    state["scraped_content"] = reader_result["messages"][-1].content
    print("scraped content",state["scraped_content"])


    ## writer chain

    research_combined = (
        f"Search RESULTS: {state['search_results']}"
        f"DETAILED_SCRAPED_CONTENT: {state['scraped_content']}"
    )

    state["report"]=writer_chain.invoke({
        "topic":topic,
        "research":research_combined
    })
    print("\n final report",state['report'])

    ##critic chain

    state["feedback"] = critic_chain.invoke({
        "report":state["report"]
    })

    print("critic report :",state["feedback"])

    return state



if __name__ == "__main__":
    topic = input("enter a research topic: ")
    run_search_pipeline(topic)