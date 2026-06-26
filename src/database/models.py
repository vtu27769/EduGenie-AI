# Database schema models module (stubs / helper fields)

class User:
    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username

class QuizRecord:
    def __init__(self, record_id: int, document_name: str, score: int, total_questions: int, taken_at: str):
        self.record_id = record_id
        self.document_name = document_name
        self.score = score
        self.total_questions = total_questions
        self.taken_at = taken_at
