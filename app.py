from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from models import db, Course, Chapter, Lesson, Schedule, TodaysTask, Quiz
from utils import (
    chapter_chain, lesson_chain, generate_schedule, content_chain, 
    quiz_chain, create_rag_vector_store, rag_answer
)
from datetime import datetime, timedelta
import json
import os
import markdown

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///courses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


@app.template_filter('markdown')
def markdown_filter(text):
    """Convert markdown text to HTML"""
    if not text:
        return ""
    html = markdown.markdown(text, extensions=['fenced_code', 'tables'])
    return html
@app.context_processor
def inject_courses():
    def get_course_names():
        courses = Course.query.all()
        return [course.course_name for course in courses]
    return dict(get_course_names=get_course_names)

@app.route('/')
def home():
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    tasks = db.session.query(
        Schedule, Course.course_name
    ).join(
        Course, Schedule.course_id == Course.course_id
    ).outerjoin(
        TodaysTask, (TodaysTask.schedule_id == Schedule.schedule_id) & (TodaysTask.date == today)
    ).filter(
        Schedule.date == today,
        (TodaysTask.completed == False) | (TodaysTask.completed == None)
    ).all()
    
    tasks_by_course = {}
    for schedule, course_name in tasks:
        if course_name not in tasks_by_course:
            tasks_by_course[course_name] = []
        tasks_by_course[course_name].append({
            'schedule_id': schedule.schedule_id,
            'task_type': schedule.task_type,
            'task_description': schedule.task_description,
            'lesson_id': schedule.lesson_id,
            'chapter_id': schedule.chapter_id  
        })
    
    return render_template('home.html', tasks_by_course=tasks_by_course, today=today)

@app.route('/new_course', methods=['GET', 'POST'])
def new_course():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'generate_chapters':
            course_name = request.form.get('course_name')
            if course_name:
                try:
                    chapter_data = chapter_chain.invoke({"course": course_name})
                    session['course_name'] = course_name
                    session['chapters'] = chapter_data.chapters[:5]
                    session['step'] = 'select_chapters'
                    return redirect(url_for('new_course'))
                except Exception as e:
                    flash(f'Error generating chapters: {str(e)}', 'error')
            else:
                flash('Please enter a course name.', 'error')
                
        elif action == 'create_course':
            selected_chapters = request.form.getlist('selected_chapters')
            course_name = session.get('course_name')
            
            if not selected_chapters:
                flash('Please select at least one chapter.', 'error')
                return redirect(url_for('new_course'))
                
            try:
                lesson_data = lesson_chain.invoke({
                    "course": course_name, 
                    "chapters": selected_chapters
                })
                
                schedule_data = generate_schedule(lesson_data.course_structure)
                
                save_course_to_db(course_name, selected_chapters, lesson_data.course_structure, schedule_data.schedule)
                
                flash('Course created successfully!', 'success')
                session.pop('course_name', None)
                session.pop('chapters', None)
                session.pop('step', None)
                return redirect(url_for('home'))
                
            except Exception as e:
                flash(f'Error creating course: {str(e)}', 'error')
    
    step = session.get('step', 'input_course')
    return render_template('new_course.html', step=step)

def save_course_to_db(course_name, chapters, lessons, schedule):
    course = Course(course_name=course_name)
    db.session.add(course)
    db.session.commit()
    
    chapter_objs = {}
    lesson_objs = {}
    
    for i, chapter_title in enumerate(chapters, 1):
        chapter = Chapter(
            course_id=course.course_id,
            chapter_title=chapter_title,
            chapter_order=i
        )
        db.session.add(chapter)
        db.session.commit()
        chapter_objs[chapter_title] = chapter
        
        if chapter_title in lessons:
            for j, lesson_title in enumerate(lessons[chapter_title].lessons, 1):
                lesson = Lesson(
                    chapter_id=chapter.chapter_id,
                    lesson_title=lesson_title,
                    lesson_order=j
                )
                db.session.add(lesson)
                db.session.commit()
                lesson_objs[lesson_title] = lesson
    
    today = datetime.now().date()
    for date_str, tasks in schedule.items():
        for task in tasks:
            task_type = "Lesson"
            lesson_id = None
            chapter_id = None
            
            if task.startswith("Short Quiz:"):
                task_type = "Short Quiz"
                lesson_title = task.replace("Short Quiz: ", "")
                lesson_id = lesson_objs.get(lesson_title).lesson_id
                chapter_id = lesson_objs.get(lesson_title).chapter_id
            elif task.startswith("Large Quiz:"):
                task_type = "Large Quiz"
                chapter_title = task.replace("Large Quiz: ", "")
                chapter_id = chapter_objs.get(chapter_title).chapter_id
            else:
                lesson_id = lesson_objs.get(task).lesson_id
                chapter_id = lesson_objs.get(task).chapter_id
            
            schedule_entry = Schedule(
                course_id=course.course_id,
                chapter_id=chapter_id,
                lesson_id=lesson_id,
                date=date_str,
                task_type=task_type,
                task_description=task
            )
            db.session.add(schedule_entry)
    
    db.session.commit()

@app.route('/course/<course_name>')
def course_detail(course_name):
    course = Course.query.filter_by(course_name=course_name).first()
    if not course:
        flash('Course not found.', 'error')
        return redirect(url_for('home'))
    
    chapters = Chapter.query.filter_by(course_id=course.course_id).order_by(Chapter.chapter_order).all()
    
    lessons = {}
    for chapter in chapters:
        chapter_lessons = Lesson.query.filter_by(chapter_id=chapter.chapter_id).order_by(Lesson.lesson_order).all()
        lessons[chapter.chapter_title] = chapter_lessons
    
    schedule_entries = Schedule.query.filter_by(course_id=course.course_id).order_by(Schedule.date).all()
    
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    return render_template('course_detail.html', 
                         course_name=course_name,
                         chapters=chapters,
                         lessons=lessons,
                         schedule=schedule_entries,
                         today=today)

@app.route('/lesson/<course_name>/<int:chapter_id>/<int:lesson_id>')
def lesson_view(course_name, chapter_id, lesson_id):
    course = Course.query.filter_by(course_name=course_name).first()
    if not course:
        flash('Course not found.', 'error')
        return redirect(url_for('home'))
    
    chapter = Chapter.query.filter_by(chapter_id=chapter_id, course_id=course.course_id).first()
    if not chapter:
        flash('Chapter not found.', 'error')
        return redirect(url_for('course_detail', course_name=course_name))
    
    lesson = Lesson.query.filter_by(lesson_id=lesson_id, chapter_id=chapter_id).first()
    if not lesson:
        flash('Lesson not found.', 'error')
        return redirect(url_for('course_detail', course_name=course_name))
    
    if not lesson.content:
        try:
            content_data = content_chain.invoke({
                "course": course_name,
                "chapter": chapter.chapter_title,
                "lesson": lesson.lesson_title
            })
            lesson.content = content_data.content
            db.session.commit()
        except Exception as e:
            # Optional: Log raw output for debugging (remove in production)
            flash(f'Error generating lesson content: {str(e)}', 'error')
    
    return render_template('lesson_view.html',
                         course_name=course_name,
                         chapter_title=chapter.chapter_title,
                         lesson_title=lesson.lesson_title,
                         content=lesson.content)

@app.route('/quiz/<course_name>/<int:chapter_id>')
@app.route('/quiz/<course_name>/<int:chapter_id>/<int:lesson_id>')
def quiz_view(course_name, chapter_id, lesson_id=None):
    course = Course.query.filter_by(course_name=course_name).first()
    if not course:
        flash('Course not found.', 'error')
        return redirect(url_for('home'))
    
    chapter = Chapter.query.filter_by(chapter_id=chapter_id, course_id=course.course_id).first()
    if not chapter:
        flash('Chapter not found.', 'error')
        return redirect(url_for('course_detail', course_name=course_name))
    
    quiz_type = "Short Quiz" if lesson_id else "Large Quiz"
    
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    if lesson_id:
        questions = Quiz.query.filter_by(
            course_id=course.course_id,
            chapter_id=chapter_id,
            lesson_id=lesson_id,
            quiz_type=quiz_type,
            date=today
        ).all()
        lesson = Lesson.query.get(lesson_id)
        lesson_title = lesson.lesson_title if lesson else None
    else:
        questions = Quiz.query.filter_by(
            course_id=course.course_id,
            chapter_id=chapter_id,
            quiz_type=quiz_type,
            date=today
        ).all()
        lesson_title = None
    
    if not questions:
        try:
            context = chapter.chapter_title
            if lesson_id and lesson:
                context += f", lesson: {lesson.lesson_title}"
            
            quiz_data = quiz_chain.invoke({
                "course": course_name,
                "chapter": context,
                "quiz_type": quiz_type
            })
            
            for question in quiz_data.questions:
                quiz = Quiz(
                    date=today,
                    course_id=course.course_id,
                    chapter_id=chapter_id,
                    lesson_id=lesson_id,
                    quiz_type=quiz_type,
                    question=question.question,
                    options=json.dumps(question.options),
                    correct_answer=question.correct_answer
                )
                db.session.add(quiz)
            db.session.commit()
            
            if lesson_id:
                questions = Quiz.query.filter_by(
                    course_id=course.course_id,
                    chapter_id=chapter_id,
                    lesson_id=lesson_id,
                    quiz_type=quiz_type,
                    date=today
                ).all()
            else:
                questions = Quiz.query.filter_by(
                    course_id=course.course_id,
                    chapter_id=chapter_id,
                    quiz_type=quiz_type,
                    date=today
                ).all()
                
        except Exception as e:
            flash(f'Error generating quiz questions: {str(e)}', 'error')
    
    questions_data = []
    for q in questions:
        questions_data.append({
            'question': q.question,
            'options': json.loads(q.options),
            'correct_answer': q.correct_answer
        })
    
    return render_template('quiz_view.html',
                         course_name=course_name,
                         chapter_title=chapter.chapter_title,
                         lesson_title=lesson_title,
                         quiz_type=quiz_type,
                         questions=questions_data)

@app.route('/ask_question', methods=['POST'])
def ask_question():
    try:
        data = request.json
        question = data.get('question')
        course_name = data.get('course_name')
        chapter_title = data.get('chapter_title')
        lesson_title = data.get('lesson_title')
        content = data.get('content')
        
        if not all([question, course_name, chapter_title, lesson_title]):
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        if not content:
            return jsonify({
                'success': False, 
                'error': 'No lesson content available to answer questions'
            })
        
        vector_store, chunks = create_rag_vector_store(content)
        answer, citation = rag_answer(question, vector_store, chunks, course_name, chapter_title, lesson_title)
        
        return jsonify({
            'success': True,
            'answer': answer,
            'citation': citation
        })
        
    except Exception as e:
        print(f"Ask question error: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        })

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.json
    answers = data.get('answers')
    questions_data = data.get('questions')
    
    try:
        today = datetime.now().date().strftime("%Y-%m-%d")
        
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mark_task_completed', methods=['POST'])
def mark_task_completed():
    data = request.json
    schedule_id = data.get('schedule_id')
    task_type = data.get('task_type')
    
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    try:
        todays_task = TodaysTask.query.filter_by(
            date=today,
            schedule_id=schedule_id
        ).first()
        
        if todays_task:
            todays_task.completed = True
        else:
            todays_task = TodaysTask(
                date=today,
                schedule_id=schedule_id,
                task_type=task_type,
                generation_status='Success',
                completed=True
            )
            db.session.add(todays_task)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def init_db():
    with app.app_context():
        db.create_all()


# Initialize database when the application starts.
init_db()


if __name__ == '__main__':
    app.run(debug=True)