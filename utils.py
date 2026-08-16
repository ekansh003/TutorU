import os
from typing import List, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.embeddings import Embeddings

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash")

class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_tensor=False).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text], convert_to_tensor=False)[0].tolist()

class ChapterSchema(BaseModel):
    chapters: List[str] = Field(description="List of 5 chapter titles")

class LessonSchema(BaseModel):
    lessons: List[str] = Field(description="List of lesson titles")

class DictionarySchema(BaseModel):
    course_structure: Dict[str, LessonSchema] = Field(description="Dictionary with chapters as keys and lesson lists as values")

class ScheduleSchema(BaseModel):
    schedule: Dict[str, List[str]] = Field(description="Dictionary with dates (YYYY-MM-DD) as keys and lists of lesson or quiz titles as values")

class LessonContentSchema(BaseModel):
    content: str = Field(description="Detailed content for the specified lesson")

class QuizQuestion(BaseModel):
    question: str = Field(description="A single quiz question")
    options: List[str] = Field(description="List of 4 answer options", min_length=4, max_length=4)
    correct_answer: str = Field(description="The correct answer")

class QuizSchema(BaseModel):
    questions: List[QuizQuestion] = Field(description="List of quiz questions")

chapter_prompt = ChatPromptTemplate.from_template(
    "Generate a list of 5 chapter titles for a course on {course} that help in fully understanding the topic. "
    "Return a JSON object with a 'chapters' key containing the list of titles."
)
chapter_chain = chapter_prompt | llm.with_structured_output(ChapterSchema)

dictionary_parser = PydanticOutputParser(pydantic_object=DictionarySchema)
lesson_prompt = ChatPromptTemplate.from_template(
    """For a course on {course}, generate a list of 3 lessons for each chapter in the list below.

Chapters:
{chapters}

Return a JSON object that matches this format exactly:

{format_instructions}
"""
)
lesson_chain = lesson_prompt.partial(format_instructions=dictionary_parser.get_format_instructions()) | llm | dictionary_parser

def generate_schedule(lessons: Dict[str, LessonSchema]) -> ScheduleSchema:
    schedule = {}
    current_date = datetime.now().date()
    day_offset = 0

    for chapter, lesson_schema in lessons.items():
        for lesson in lesson_schema.lessons:
            date_str = (current_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            schedule[date_str] = [lesson, f"Short Quiz: {lesson}"]
            day_offset += 1
        date_str = (current_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        schedule[date_str] = [f"Large Quiz: {chapter}"]
        day_offset += 1

    return ScheduleSchema(schedule=schedule)

content_prompt = ChatPromptTemplate.from_template(
    """Generate detailed content for a lesson in a course. The course is "{course}", the chapter is "{chapter}", and the lesson is "{lesson}". Provide a comprehensive explanation suitable for a beginner, including key concepts, examples, and practical applications. Format the content in markdown with clear headings (##), paragraphs, lists, and code blocks where appropriate.

IMPORTANT: Respond with ONLY the following JSON object. Do not include any additional text, explanations, or Markdown formatting (e.g., no ```json

{{"content": "<insert the full markdown-formatted lesson content here as a single escaped string>"}}"""
)
content_chain = content_prompt | llm.with_structured_output(LessonContentSchema)

quiz_prompt = ChatPromptTemplate.from_template(
    """Generate a {quiz_type} for a course on {course}. The context is "{chapter}".
    A Short Quiz should have 5 questions, and a Large Quiz should have 10 questions.
    Each question should have exactly 4 answer options and one correct answer.
    Provide beginner-friendly questions with clear explanations.
    Return a JSON object with a 'questions' key containing a list of questions, each with 'question', 'options', and 'correct_answer'."""
)
quiz_chain = quiz_prompt | llm | PydanticOutputParser(pydantic_object=QuizSchema)

def create_rag_vector_store(content: str):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n## ", "\n\n", "\n", ". "]
    )
    chunks = text_splitter.split_text(content)
    embedder = SentenceTransformerEmbeddings('all-MiniLM-L6-v2')
    vector_store = FAISS.from_texts(chunks, embedder)
    return vector_store, chunks

rag_prompt = ChatPromptTemplate.from_template(
    """You are a helpful tutor explaining concepts clearly and concisely.

STUDENT QUESTION: "{question}"

LESSON CONTEXT:
Course: {course_name}
Chapter: {chapter_title} 
Lesson: {lesson_title}

RELEVANT CONTENT:
{context}

RESPONSE GUIDELINES:
- **Length**: Match the complexity of the question
  * Simple questions (what is X?): 1-2 paragraphs
  * Medium questions (how does X work?): 2-3 paragraphs  
  * Complex questions (explain X in detail): 3-4 paragraphs
- **Format**: Use clear headings, bullet points, and emphasis
- **Style**: Conversational but professional
- **Focus**: Explain concepts clearly with 1-2 good examples

IMPORTANT: Use **bold** for key terms and *italics* for emphasis. Structure your answer with clear sections.

Your explanation:"""
)

def rag_answer(question: str, vector_store, chunks, course_name: str, chapter_title: str, lesson_title: str):
    try:
        docs = vector_store.similarity_search(question, k=3)
        
        context_parts = []
        for i, doc in enumerate(docs):
            context_parts.append(f"{doc.page_content}")
        
        context = "\n\n".join(context_parts)
        
        response_chain = rag_prompt | llm
        result = response_chain.invoke({
            "course_name": course_name,
            "chapter_title": chapter_title,
            "lesson_title": lesson_title,
            "context": context,
            "question": question
        })
        
        answer = result.content
        
        citation = f'\n\n<small class="text-muted"><i class="fas fa-book me-1"></i>Reference: {lesson_title}</small>'
        
        return answer + citation, "Formatted explanation"
        
    except Exception as e:
        print(f"RAG Error: {str(e)}")
        return f"I'm having trouble accessing the lesson content right now. Please try rephrasing your question.", "[System issue]"