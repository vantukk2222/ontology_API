# app/routes/auth.py
from flask import Blueprint, jsonify, request
from app.utils import execute_query
import bcrypt

auth_bp = Blueprint('auth', __name__)

# Register a new user
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    # Check if username already exists
    query = "MATCH (u:User {username: $username}) RETURN u"
    params = {'username': username}
    result = execute_query(query, params)

    if result:
        return jsonify({'message': 'Username already exists'}), 400

    # Hash the password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create the User node in Neo4j
    query = (
        "CREATE (u:User {username: $username, password: $password, role: $role}) RETURN u"
    )
    params = {'username': username, 'password': hashed_password, 'role': role}
    result = execute_query(query, params)

    user = result[0]
    element_id = user['u'].get('elementId', None)

    return jsonify({'message': 'User registered successfully', 'username': username, 'role': role, 'elementId': element_id}), 201

# Login a user
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    # Find the user in Neo4j
    query = "MATCH (u:User {username: $username}) RETURN u.password AS password, u.role AS role, elementId(u) AS elementId"
    params = {'username': username}
    result = execute_query(query, params)

    if not result:
        return jsonify({'message': 'Invalid username or password'}), 401

    hashed_password = result[0]['password']
    role = result[0]['role']
    element_id = result[0]['elementId']

    # Check the password using bcrypt
    if not hashed_password:
        return jsonify({'message': 'Invalid password format: Password hash is missing.'}), 500
    
    try:
        if not bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
            return jsonify({'message': 'Invalid username or password'}), 401
    except ValueError as e:
        return jsonify({'message': f'Invalid password format: {str(e)}'}), 500

    return jsonify({'message': 'Login successful', 'username': username, 'role': role, 'elementId': element_id}), 200

#