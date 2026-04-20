import streamlit as st
import pandas as pd
import duckdb
import re
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

api = FastAPI()
api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class QueryRequest(BaseModel):
    question: str
    columns: list[str]
    rows: list[dict]

@api.post("/ask")
async def ask(req: QueryRequest):
    df = pd.DataFrame(req.rows, columns=req.columns)
    schema = "\n".join([f"- {c}" for c in req.columns])

    prompt = f"""
    You have a DuckDB table named 'data' with columns:
    {schema}
    User question: "{req.question}"
    Return ONLY a raw SQL SELECT query. No explanation. No markdown.
    """
    res = client.chat.completions.create(
        model="nvidia/nemotron-super-49b-v1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=512
    )
    sql = res.choices[0].message.content.strip()
    sql = re.sub(r"```sql|```", "", sql).strip()

    con = duckdb.connect()
    con.register("data", df)
    result_df = con.execute(sql).df()
    con.close()

    insight_res = client.chat.completions.create(
        model="nvidia/nemotron-super-49b-v1",
        messages=[{"role": "user", "content": f"Question: {req.question}\nResult: {result_df.head(10).to_string(index=False)}\nGive one short business insight. No preamble."}],
        temperature=0.7,
        max_tokens=256
    )

    return {
        "sql": sql,
        "columns": list(result_df.columns),
        "rows": result_df.head(50).to_dict(orient="records"),
        "insight": insight_res.choices[0].message.content
    }

def run_api():
    uvicorn.run(api, host="0.0.0.0", port=8000)

if 'api_started' not in st.session_state:
    t = threading.Thread(target=run_api, daemon=True)
    t.start()
    st.session_state['api_started'] = True

st.success("✅ AI Backend is running on port 8000. Go to Power BI and ask your question.")