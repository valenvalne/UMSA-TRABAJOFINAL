import os
import json
import logging
import requests
from typing import Any, Tuple, List, Dict

logger = logging.getLogger(__name__)

# Modelos recomendados por proveedor
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")


def get_available_ai_provider() -> Dict[str, Any]:
    """
    Detecta los proveedores de IA configurados en las variables de entorno.
    Retorna un diccionario con el proveedor activo y su configuración.
    Prioridad:
    1. GEMINI_API_KEY (Google AI Studio - gratis, sin tarjeta)
    2. GROQ_API_KEY (Groq - Llama 3.3 70B gratis y ultra rápido)
    3. ANTHROPIC_API_KEY (Anthropic Claude)
    4. OPENAI_API_KEY (OpenAI GPT)
    5. OLLAMA_BASE_URL (Ollama local)
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    ollama_url = os.getenv("OLLAMA_BASE_URL", "").strip()

    providers = []
    if gemini_key:
        providers.append({"id": "gemini", "name": "Google Gemini", "model": DEFAULT_GEMINI_MODEL, "key": gemini_key})
    if groq_key:
        providers.append({"id": "groq", "name": "Groq (Llama 3.3)", "model": DEFAULT_GROQ_MODEL, "key": groq_key})
    if anthropic_key and anthropic_key.startswith("sk-ant-"):
        providers.append({"id": "anthropic", "name": "Anthropic Claude", "model": DEFAULT_CLAUDE_MODEL, "key": anthropic_key})
    if openai_key and openai_key.startswith("sk-"):
        providers.append({"id": "openai", "name": "OpenAI", "model": DEFAULT_OPENAI_MODEL, "key": openai_key})
    if ollama_url:
        providers.append({"id": "ollama", "name": "Ollama Local", "model": os.getenv("OLLAMA_MODEL", "llama3.2"), "url": ollama_url})

    return {
        "active": providers[0] if providers else None,
        "all_configured": providers,
        "has_ai": len(providers) > 0,
    }


def convert_tools_to_openai_format(tools_list: List[Dict]) -> List[Dict]:
    """Convierte la lista de tools a formato OpenAI/Groq."""
    openai_tools = []
    for t in tools_list:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            }
        })
    return openai_tools


def convert_tools_to_gemini_format(tools_list: List[Dict]) -> List[Dict]:
    """Convierte la lista de tools a formato Gemini."""
    declarations = []
    for t in tools_list:
        schema = t.get("input_schema", {"type": "object", "properties": {}})
        # Asegurar tipos compatibles con Gemini
        declarations.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": schema,
        })
    return [{"functionDeclarations": declarations}] if declarations else []


def call_gemini_api(
    api_key: str,
    model: str,
    system_prompt: str,
    messages: List[Dict],
    tools_list: List[Dict],
    execute_tool_cb=None,
    module: str = "",
) -> Tuple[str, List[Dict]]:
    """
    Ejecuta llamada a la API de Google Gemini con soporte para Tool Calling y multi-turn.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    # Formatear contenidos
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        content = m["content"]
        if isinstance(content, str):
            contents.append({"role": role, "parts": [{"text": content}]})
        elif isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append({"text": item})
                elif isinstance(item, dict) and item.get("text"):
                    parts.append({"text": item["text"]})
            if parts:
                contents.append({"role": role, "parts": parts})

    tools_payload = convert_tools_to_gemini_format(tools_list)
    body: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 2048,
        }
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    if tools_payload:
        body["tools"] = tools_payload

    tool_records = []
    max_turns = 5
    turn = 0

    while turn < max_turns:
        turn += 1
        resp = requests.post(url, headers=headers, json=body, timeout=45)
        if resp.status_code != 200:
            raise RuntimeError(f"Error Gemini API ({resp.status_code}): {resp.text}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return "No se recibió respuesta del modelo.", tool_records

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        # Revisar si hay llamados a funciones (tool calling)
        function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
        text_parts = [p["text"] for p in parts if "text" in p]

        if function_calls and execute_tool_cb:
            # Añadir respuesta del modelo a los contenidos
            body["contents"].append(content)
            response_parts = []
            for fc in function_calls:
                fn_name = fc["name"]
                fn_args = fc.get("args", {})
                try:
                    tool_res = execute_tool_cb(fn_name, fn_args, module)
                    tool_records.append({"tool": fn_name, "input": fn_args, "result": str(tool_res)})
                    res_val = tool_res
                except Exception as exc:
                    tool_records.append({"tool": fn_name, "input": fn_args, "error": str(exc)})
                    res_val = f"Error: {exc}"

                response_parts.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": {"name": fn_name, "content": res_val}
                    }
                })

            body["contents"].append({"role": "function", "parts": response_parts})
            continue

        final_text = "".join(text_parts).strip()
        return final_text, tool_records

    return "Límite de iteraciones alcanzado.", tool_records


def call_openai_compatible_api(
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    messages: List[Dict],
    tools_list: List[Dict],
    execute_tool_cb=None,
    module: str = "",
) -> Tuple[str, List[Dict]]:
    """
    Ejecuta llamada a una API compatible con OpenAI (Groq, OpenAI, OpenRouter, Ollama).
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if api_key else "",
    }
    api_messages = [{"role": "system", "content": system_prompt}]
    for m in messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    formatted_tools = convert_tools_to_openai_format(tools_list)
    body: Dict[str, Any] = {
        "model": model,
        "messages": api_messages,
        "temperature": 0.4,
        "max_tokens": 2048,
    }
    if formatted_tools:
        body["tools"] = formatted_tools
        body["tool_choice"] = "auto"

    tool_records = []
    max_turns = 5
    turn = 0

    while turn < max_turns:
        turn += 1
        resp = requests.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=body, timeout=45)
        if resp.status_code != 200:
            raise RuntimeError(f"Error LLM API ({resp.status_code}): {resp.text}")

        data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        tool_calls = msg.get("tool_calls", [])

        if tool_calls and execute_tool_cb:
            body["messages"].append(msg)
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except Exception:
                    fn_args = {}

                try:
                    tool_res = execute_tool_cb(fn_name, fn_args, module)
                    tool_records.append({"tool": fn_name, "input": fn_args, "result": str(tool_res)})
                    content_str = str(tool_res)
                except Exception as exc:
                    tool_records.append({"tool": fn_name, "input": fn_args, "error": str(exc)})
                    content_str = f"Error: {exc}"

                body["messages"].append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": content_str,
                })
            continue

        return msg.get("content", "").strip(), tool_records

    return "Límite de iteraciones alcanzado.", tool_records


def call_anthropic_api(
    api_key: str,
    model: str,
    system_prompt: str,
    messages: List[Dict],
    tools_list: List[Dict],
    execute_tool_cb=None,
    module: str = "",
) -> Tuple[str, List[Dict]]:
    """
    Ejecuta llamada a Anthropic Claude.
    """
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    anthropic_messages = []
    for m in messages:
        anthropic_messages.append({"role": m["role"], "content": m["content"]})

    tool_records = []
    while True:
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=anthropic_messages,
            tools=tools_list,
        )
        assistant_content = resp.content
        anthropic_messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for block in assistant_content:
            if block.type == "tool_use":
                try:
                    res = execute_tool_cb(block.name, block.input, module)
                    tool_records.append({"tool": block.name, "input": block.input, "result": str(res)})
                except Exception as exc:
                    res = f"Error ejecutando {block.name}: {exc}"
                    tool_records.append({"tool": block.name, "input": block.input, "error": str(exc)})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(res),
                })

        if not tool_results:
            answer = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
            return answer, tool_records

        anthropic_messages.append({"role": "user", "content": tool_results})


def query_llm_intelligence(
    system_prompt: str,
    messages: List[Dict],
    tools_list: List[Dict],
    execute_tool_cb,
    module: str = "",
) -> Tuple[str | None, List[Dict], str | None]:
    """
    Intenta consultar los proveedores de IA configurados en orden de prioridad.
    Si uno falla (por ejemplo por saldo agotado de Anthropic), intenta automáticamente
    con el siguiente proveedor antes de retornar None.
    Retorna: (respuesta_texto, tool_records, nombre_proveedor_usado)
    """
    provider_info = get_available_ai_provider()
    configured = provider_info["all_configured"]

    if not configured:
        return None, [], None

    last_error = None
    for prov in configured:
        p_id = prov["id"]
        try:
            if p_id == "gemini":
                ans, tools_rec = call_gemini_api(
                    api_key=prov["key"],
                    model=prov["model"],
                    system_prompt=system_prompt,
                    messages=messages,
                    tools_list=tools_list,
                    execute_tool_cb=execute_tool_cb,
                    module=module,
                )
                return ans, tools_rec, "Google Gemini"

            elif p_id == "groq":
                ans, tools_rec = call_openai_compatible_api(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=prov["key"],
                    model=prov["model"],
                    system_prompt=system_prompt,
                    messages=messages,
                    tools_list=tools_list,
                    execute_tool_cb=execute_tool_cb,
                    module=module,
                )
                return ans, tools_rec, "Groq (Llama 3.3)"

            elif p_id == "openai":
                ans, tools_rec = call_openai_compatible_api(
                    base_url="https://api.openai.com/v1",
                    api_key=prov["key"],
                    model=prov["model"],
                    system_prompt=system_prompt,
                    messages=messages,
                    tools_list=tools_list,
                    execute_tool_cb=execute_tool_cb,
                    module=module,
                )
                return ans, tools_rec, "OpenAI"

            elif p_id == "anthropic":
                ans, tools_rec = call_anthropic_api(
                    api_key=prov["key"],
                    model=prov["model"],
                    system_prompt=system_prompt,
                    messages=messages,
                    tools_list=tools_list,
                    execute_tool_cb=execute_tool_cb,
                    module=module,
                )
                return ans, tools_rec, "Anthropic Claude"

            elif p_id == "ollama":
                ans, tools_rec = call_openai_compatible_api(
                    base_url=f"{prov['url'].rstrip('/')}/v1",
                    api_key="ollama",
                    model=prov["model"],
                    system_prompt=system_prompt,
                    messages=messages,
                    tools_list=tools_list,
                    execute_tool_cb=execute_tool_cb,
                    module=module,
                )
                return ans, tools_rec, "Ollama Local"

        except Exception as exc:
            logger.warning(f"Proveedor {prov['name']} falló: {exc}. Intentando siguiente proveedor...")
            last_error = exc
            continue

    logger.error(f"Todos los proveedores de IA fallaron o están sin crédito. Último error: {last_error}")
    return None, [], None
