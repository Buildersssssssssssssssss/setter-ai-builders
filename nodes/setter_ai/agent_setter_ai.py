from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt.tool_node import ToolNode

from nodes.setter_ai.prompt import build_setter_prompt
from nodes.setter_ai.tools import tools_setter_ai

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)
llm_with_tools = llm.bind_tools(tools_setter_ai)


def call_model_setter_ai(state: dict) -> dict:
    system_prompt = SystemMessage(content=build_setter_prompt(state))
    messages = state.get("messages", [])

    try:
        response = llm_with_tools.invoke([system_prompt] + messages)
    except Exception as e:
        print(f"[SETTER_AI] Error al invocar LLM: {e}")
        response = AIMessage(content="Lo siento, hubo un error procesando tu mensaje.")

    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"[SETTER_AI] Tools a ejecutar: {[tc['name'] for tc in response.tool_calls]}")
    else:
        print(f"[SETTER_AI] Respuesta de texto: {response.content[:80]!r}")

    return {"messages": [response]}


def tools_condition_setter_ai(state: dict) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "__end__"


def safe_tool_node_setter_ai(state: dict) -> dict:
    try:
        return ToolNode(tools_setter_ai).invoke(state)
    except Exception as e:
        print(f"[SETTER_AI] Error en tool node: {e}")
        return {"messages": [AIMessage(content="Error al ejecutar la herramienta.")]}
