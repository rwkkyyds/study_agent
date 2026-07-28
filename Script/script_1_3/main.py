import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing  import List
app = FastAPI()
students_db = {}
class Student(BaseModel):
    id:int
    name:str
    age:int
    scores:List[float]
@app.post("/students/")
def students(student: Student):
    students_db[student.id] = student
    average_score = sum(student.scores) / len(student.scores) if student.scores else 0
    return {"name": student.name, "age": student.age, "average_score": average_score}

@app.get("/students/{student_id}" )
def get_student(student_id: int):
    try:
        student = students_db.get(student_id)
        if not student:
            return {"error": "Student not found"}
    except KeyError:
        return {"error": "Student not found"}
    return {"student_id": student.id, "name": student.name, "age": student.age, "average_score": sum(student.scores) / len(student.scores) if student.scores else 0}






from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
prompt  = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的助手，帮助用户解释技术概念。请用JSON格式回答，包含 concept 和 explanation 字段。"),
    ("human", "请解释一下什么是 {concept}？")
])
llm = ChatOpenAI(
    api_key=os.getenv("ZHIPU_API_KEY", ""),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    model="glm-4-flash",
    temperature=0.7,
)
parser = JsonOutputParser()
chain = prompt | llm | parser
concepts = ["RAG", "Embedding", "向量数据库"]
for concept in concepts:
    result = chain.invoke({"concept": concept})
    print(f"{concept} -> {result}")







from langchain_text_splitters import RecursiveCharacterTextSplitter

text = """人工智能（Artificial Intelligence，AI）是计算机科学的一个分支。
它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
深度学习是机器学习的分支，是一种以人工神经网络为架构，对数据进行表征学习的算法。
自然语言处理（NLP）是人工智能的重要方向，让计算机理解和生成人类语言。
大语言模型（LLM）是NLP领域的突破性进展，GPT、Claude、GLM都是代表性的LLM。"""

text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, 
                                               chunk_overlap=20,
                                               separators=["\n\n", "\n", " ", ""])
chunks = text_splitter.split_text(text)
for i,chunk in enumerate(chunks):
    print(f"块{i+1}: {len(chunk)}字符")
    print(f"  {chunk}")
    print()
print(f"总共分成了 {len(chunks)} 块",
      "average chunk size:", sum(len(c) for c in chunks)//len(chunks),"字符",
      "max chunk size:", max(len(c) for c in chunks),"字符",
      "min chunk size:", min(len(c) for c in chunks),"字符")









#1.pydantic作用
#1.数据验证：确保输入数据符合预期格式和类型，自动抛出错误提示。
#2.数据解析：将输入数据转换为Python对象，方便后续处理.
#3.自动文档生成：与FastAPI集成，自动生成API文档，提升开发效率。
#4.数据序列化：支持将Python对象转换为JSON等格式，便于数据传输和存储。
# response_model参数可以指定返回数据的结构，FastAPI会自动使用pydantic进行验证和序列化。
#5.类型提示：提供类型提示，增强代码可读性和开发体验。
#总结：pydantic在FastAPI中扮演着数据验证和解析的关键角色，确保API的健壮性和易用性.


#2. LCEL 的 | 管道符创建了什么对象？数据如何流动？
# LCEL 的 | 管道符创建了一个新的 Runnable 对象，代表了整个链路的组合。
# 数据流动：当调用链的 invoke() 方法时，输入数据首先进入第一个组件（如 Prompt），
# 处理后输出结果传递给下一个组件（如 LLM），依此类推，直到最后一个组件（如 Parser）输出最终结果。
# 这种设计使得链路的组合非常灵活，组件之间的数据传递

#

#3. RecursiveCharacterTextSplitter 的分隔符优先级是什么？
#\\n\\n > \\n > 。> 空格 > ，> 字符
# 优先使用双换行分隔文本，如果没有双换行，则使用单换
#行分隔，如果没有单换行，则使用空格分隔，最后如果都没有，则按字符分割。
# 这种优先级设计是为了尽可能保持文本的语义完整性，
# 避免在不合适的位置切断文本，同时又能保证块的大小符合要求.




# 4. chunk_overlap 设为 0 会导致什么问题？
# chunk_overlap 设为 0 会导致分块之间没有重叠部分，可能会切断一些重要的上下文信息.




# 5. Document 对象的 page_content 和 metadata 分别存什么？
# page_content 存储的是文档的文本内容
#metadata 存储的是与文档相关的元信息，如来源文件路径、分块索引等，便于后续检索和管理.






#6. 为什么 RAG 需要分块，不能直接把整篇文档给 LLM？
    #.LLM的输入有上下文限制，直接输入整篇文档可能超过限制，导致无法处理。
    #.分块可以提高检索效率，LLM只需要处理相关的块，而不是整篇文档。
    #.分块可以增强回答的准确性，LLM基于相关块生成回答，减少无关信息干扰。
    #.分块可以支持更大的文档库，LLM不需要一次性加载所有文档，节省计算资源。
    #.分块可以实现更细粒度的检索，用户问题可能只涉及文档的某个部分，分块后更容易找到相关内容。






















