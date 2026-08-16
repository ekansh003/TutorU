from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Course(db.Model):
    __tablename__ = 'courses'
    course_id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    chapters = db.relationship('Chapter', backref='course', cascade='all, delete-orphan')

class Chapter(db.Model):
    __tablename__ = 'chapters'
    chapter_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    chapter_title = db.Column(db.String(200), nullable=False)
    chapter_order = db.Column(db.Integer, nullable=False)
    
    lessons = db.relationship('Lesson', backref='chapter', cascade='all, delete-orphan')
    schedule_entries = db.relationship('Schedule', backref='chapter', cascade='all, delete-orphan')

class Lesson(db.Model):
    __tablename__ = 'lessons'
    lesson_id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.chapter_id'), nullable=False)
    lesson_title = db.Column(db.String(200), nullable=False)
    lesson_order = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text)
    
    schedule_entries = db.relationship('Schedule', backref='lesson', cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', backref='lesson', cascade='all, delete-orphan')

class Schedule(db.Model):
    __tablename__ = 'schedule'
    schedule_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.chapter_id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.lesson_id'))
    date = db.Column(db.String(10), nullable=False) 
    task_type = db.Column(db.String(20), nullable=False) 
    task_description = db.Column(db.String(300), nullable=False)
    
    todays_tasks = db.relationship('TodaysTask', backref='schedule', cascade='all, delete-orphan')

class TodaysTask(db.Model):
    __tablename__ = 'todays_tasks'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)  
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.schedule_id'), nullable=False)
    task_type = db.Column(db.String(20), nullable=False)
    generation_status = db.Column(db.String(20), default='Pending')  
    completed = db.Column(db.Boolean, default=False)

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    quiz_id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.chapter_id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.lesson_id'))
    quiz_type = db.Column(db.String(20), nullable=False)  
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)  
    correct_answer = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer)
    
    def get_options(self):
        return json.loads(self.options)
    
    def set_options(self, options_list):
        self.options = json.dumps(options_list)