# app/routes/user.py
from flask import Blueprint, jsonify, request
from app.utils import execute_query
import bcrypt

user_bp = Blueprint('user', __name__)

# Add a new user
@user_bp.route('/user/add-user', methods=['POST'])
def add_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    name = data.get('name')
    birth_date = data.get('birth_date')
    student_id = data.get('student_id')
    email = data.get('email')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    # Check if username, student_id, or email already exists
    query = "MATCH (u:User) WHERE u.username = $username OR u.student_id = $student_id OR u.email = $email RETURN u"
    params = {'username': username, 'student_id': student_id, 'email': email}
    result = execute_query(query, params)

    if result:
        return jsonify({'message': 'Username, student ID, or email already exists'}), 400

    # Hash the password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create the User node in Neo4j
    query = (
        "CREATE (u:User {username: $username, password: $password, role: $role, name: $name, birth_date: $birth_date, student_id: $student_id, email: $email}) RETURN elementId(u) AS element_id, u"
    )
    params = {'username': username, 'password': hashed_password, 'role': role, 'name': name, 'birth_date': birth_date, 'student_id': student_id, 'email': email}
    result = execute_query(query, params)

    user = result[0]
    element_id = user.get('element_id', None)

    return jsonify({'message': 'User added successfully', 'username': username, 'role': role, 'elementId': element_id}), 201

# Update an existing user
@user_bp.route('/user/update-user/<user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json()
    new_username = data.get('username')
    new_role = data.get('role')
    new_name = data.get('name')
    new_birth_date = data.get('birth_date')
    new_student_id = data.get('student_id')
    new_email = data.get('email')

    # Check if the user exists
    query = "MATCH (u:User) WHERE elementId(u) = $user_id RETURN u"
    params = {'user_id': user_id}
    result = execute_query(query, params)

    if not result:
        return jsonify({'message': f'User with id {user_id} does not exist'}), 404

    # Check if the new student_id or email already exists for another user
    if new_student_id or new_email:
        query = "MATCH (u:User) WHERE (u.student_id = $student_id OR u.email = $email) AND elementId(u) <> $user_id RETURN u"
        params.update({'student_id': new_student_id, 'email': new_email})
        existing_user = execute_query(query, params)
        if existing_user:
            return jsonify({'message': 'Student ID or email already exists for another user'}), 400

    # Update the user's information
    update_query = "MATCH (u:User) WHERE elementId(u) = $user_id "
    if new_username:
        update_query += "SET u.username = $new_username "
    if new_role:
        update_query += "SET u.role = $new_role "
    if new_name:
        update_query += "SET u.name = $new_name "
    if new_birth_date:
        update_query += "SET u.birth_date = $new_birth_date "
    if new_student_id:
        update_query += "SET u.student_id = $new_student_id "
    if new_email:
        update_query += "SET u.email = $new_email "

    params.update({'new_username': new_username, 'new_role': new_role, 'new_name': new_name, 'new_birth_date': new_birth_date, 'new_student_id': new_student_id, 'new_email': new_email})
    execute_query(update_query, params)

    return jsonify({'message': 'User updated successfully', 'user_id': user_id}), 200

# Delete an existing user
@user_bp.route('/user/delete-user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    # Check if the user exists
    query = "MATCH (u:User) WHERE elementId(u) = $user_id RETURN u"
    params = {'user_id': user_id}
    result = execute_query(query, params)

    if not result:
        return jsonify({'message': f'User with id {user_id} does not exist'}), 404

    # Delete the user node in Neo4j
    delete_query = "MATCH (u:User) WHERE elementId(u) = $user_id DETACH DELETE u"
    execute_query(delete_query, params)

    return jsonify({'message': f'User with id {user_id} deleted successfully'}), 200

# Get a user by user_id
@user_bp.route('/user/get-user/<user_id>', methods=['GET'])
def get_user(user_id):
    # Check if the user exists
    query = "MATCH (u:User) WHERE elementId(u) = $user_id RETURN u"
    params = {'user_id': user_id}
    result = execute_query(query, params)

    if not result:
        return jsonify({'message': f'User with id {user_id} does not exist'}), 404

    user = result[0]['u']
    user_data = {
        'user_id': user_id,
        'username': user['username'],
        'role': user['role'],
        'name': user.get('name', ''),
        'birth_date': user.get('birth_date', ''),
        'student_id': user.get('student_id', ''),
        'email': user.get('email', '')
    }

    return jsonify({'user': user_data}), 200

# Get all users
@user_bp.route('/user/get-all-users', methods=['GET'])
def get_all_users():
    query = "MATCH (u:User) RETURN elementId(u) AS user_id, u.username AS username, u.role AS role, u.name AS name, u.birth_date AS birth_date, u.student_id AS student_id, u.email AS email"
    result = execute_query(query)

    users = [
        {
            'user_id': record['user_id'],
            'username': record['username'],
            'role': record['role'],
            'name': record.get('name', ''),
            'birth_date': record.get('birth_date', ''),
            'student_id': record.get('student_id', ''),
            'email': record.get('email', '')
        }
        for record in result
    ]

    return jsonify({'users': users}), 200


# Change password
@user_bp.route('/user/change-password/<user_id>', methods=['PUT'])
def change_password(user_id):
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({'message': 'Old password and new password are required'}), 400

    # Check if the user exists
    query = "MATCH (u:User) WHERE elementId(u) = $user_id RETURN u.password AS password"
    params = {'user_id': user_id}
    result = execute_query(query, params)

    if not result:
        return jsonify({'message': f'User with id {user_id} does not exist'}), 404

    hashed_password = result[0]['password']

    # Verify the old password
    if not bcrypt.checkpw(old_password.encode('utf-8'), hashed_password.encode('utf-8')):
        return jsonify({'message': 'Old password is incorrect'}), 400

    # Hash the new password
    new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Update the password in the database
    update_query = "MATCH (u:User) WHERE elementId(u) = $user_id SET u.password = $new_password"
    params.update({'new_password': new_hashed_password})
    execute_query(update_query, params)

    return jsonify({'message': 'Password updated successfully'}), 200
