from src.database.db_manager import authenticate_user

result = authenticate_user("testuser999", "Test@123")
print(result)