# Theatre API project

A comprehensive REST API for theatre management, enabling ticket reservations, performance scheduling, and review management. Built with Django REST Framework and featuring JWT authentication.

## Installation using GitHub
Python 3.11 must be already installed  
git clone https://github.com/viktoriaom/theatre-api  
cd theatre_api  
create .env file based on the example

## Local Setup with SQLite
python3 -m venv venv  
source venv/bin/activate # creates virtual environment on macOS/Linux    
venv\Scripts\activate # creates virtual environment on Windows  
pip install -r requirements.txt  
python manage.py makemigrations # creates migrations    
python manage.py migrate # creates DB  
python manage.py runserver # starts Django server    

The API will be available at http://127.0.0.1:8000/  

# Optional
Load test data into db:  
python manage.py loaddata fixtures/theatre_data.json


## Run with Docker and PostgreSQL
docker-compose build  
docker-compose up  

The API will be available at `http://127.0.0.1:8002/

# Optional
Load test data into db:  
docker-compose exec theatre python manage.py loaddata fixtures/theatre_data.json


## Getting Access
* register a new user via api/user/register  
* get access token via api/user/token  
* Include the token in your request headers:  
Authorization: Bearer <your-access-token>

# Demo Credentials
For testing purposes only:
**email:** first_user@theatre.com  
**password:** qazxsw


## Features
### Core functionality
* Play Management - Create and manage theatrical productions
* Reservation System - Book tickets with seat selection
* Review & Rating - User reviews with automatic rating calculations
* Performance Scheduling - Schedule and manage show times
* Theatre Hall Management - Configure venues and seating

### Technical features
* JWT Authentication - Secure token-based authentication
* Email-based Login - Username field replaced with email
* Advanced Filtering - Filter by genre, actor, play, date, user, performance
* Pagination - Paginated results for large datasets
* Rate Limiting - API throttling to prevent abuse
* Image Upload - Attach images to plays
* Role-based Permissions - Custom permission classes
* API Documentation - Interactive Swagger/ReDoc docs
* Comprehensive Tests - Full test coverage for custom features
  

## Built With
* Django [https://www.djangoproject.com] - Web framework  
* Django REST Framework [https://www.django-rest-framework.org] - API toolkit  
* PostgreSQL [https://www.postgresql.org] - Database  
* SQLite [https://sqlite.org] - Database  
* JWT [https://www.jwt.io] - Authentication  
* Docker [https://www.docker.com] - Containerization  
* drf-spectacular [https://drf-spectacular.readthedocs.io] - API documentation  


## Usage Tips
* Users can create reservations & reviews  
* Admins can create & delete all resources  
* Admins can add images to plays  
* Reservations and reviews cannot be modified once created  
* Users can only access their own reservations  
* Admins can access and filter all reservations by user and performance  
* Tickets are always linked to reservations; there are no separate ticket endpoints  
* Permissions are enforced on most views using custom IsAdminOrIfAuthenticatedReadOnly permission class  
* Reviews and reservations use HTTP method restrictions and standard IsAdminUser / IsAuthenticated permission classes
