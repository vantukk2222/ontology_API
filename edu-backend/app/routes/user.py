# app/routes/user.py
from flask import Blueprint, jsonify, request
from app.utils import execute_query
import bcrypt

user_bp = Blueprint('user', __name__)

# Add a new user
@user_bp.route('/add-user', methods=['POST'])
def add_user():
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

    return jsonify({'message': 'User added successfully', 'username': username, 'role': role, 'elementId': element_id}), 201

# Update an existing user
@user_bp.route('/update-user/<user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json()
    new_username = data.get('username')
    new_role = data.get('role')

    # Check if the user exists
    query = "MATCH (u:User) WHERE elementId(u) = $user_id RETURN u"
    params = {'user_id': user_id}
    result = execute_query(query, params)

    if not result:
        return jsonify({'message': f'User with id {user_id} does not exist'}), 404

    # Update the user's information
    update_query = "MATCH (u:User) WHERE elementId(u) = $user_id "
    if new_username:
        update_query += "SET u.username = $new_username "
    if new_role:
        update_query += "SET u.role = $new_role "

    params.update({'new_username': new_username, 'new_role': new_role})
    execute_query(update_query, params)

    return jsonify({'message': 'User updated successfully', 'user_id': user_id}), 200

# Delete an existing user
@user_bp.route('/delete-user/<user_id>', methods=['DELETE'])
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
