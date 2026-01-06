from langgraph.graph import END  # NOT tkinter.END

tags=["router"]
def route_after_actions_join(state):
    return "go_review" if state.get("join_ready") else END


