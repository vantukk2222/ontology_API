# app/routes/courses.py
from flask import Blueprint, jsonify, request
from app.utils import execute_query

# Utility functions
def check_existing_course(course_id):
    query = """
    MATCH (course) WHERE elementId(course) = $course_id
    RETURN course
    """
    params = {'course_id': course_id}
    return execute_query(query, params)

def check_existing_target(target_id):
    query = """
    MATCH (target) WHERE elementId(target) = $target_id
    RETURN target
    """
    params = {'target_id': target_id}
    return execute_query(query, params)

def check_existing_relation(course_id, target_id, relation_type):
    query = """
    MATCH (course)-[rel:`{relation_type}`]->(target)
    WHERE elementId(course) = $course_id AND elementId(target) = $target_id
    RETURN rel
    """
    params = {
        'course_id': course_id,
        'target_id': target_id
    }
    return execute_query(query, params)

def check_prerequisite_violation(course_id, target_id):
    # Check if course A is a prerequisite of course B and both are in the same semester
    query = """
    MATCH (courseA)-[:ns0__tienQuyet]->(courseB)
    WHERE elementId(courseA) = $course_id AND elementId(courseB) = $target_id AND courseA.ns0__hocKy = courseB.ns0__hocKy
    RETURN courseA, courseB
    """
    params = {
        'course_id': course_id,
        'target_id': target_id
    }
    return execute_query(query, params)

def check_parallel_violation(course_id, target_id):
    # Check if two courses are in a parallel relationship but cannot be taken in the same semester
    query = """
    MATCH (courseA)-[:ns0__songHanh]->(courseB)
    WHERE elementId(courseA) = $course_id AND elementId(courseB) = $target_id AND courseA.ns0__hocKy <> courseB.ns0__hocKy
    RETURN courseA, courseB
    """
    params = {
        'course_id': course_id,
        'target_id': target_id
    }
    return execute_query(query, params)

def check_prior_violation(course_id, target_id):
    # Check if course A must be taken before course B but both are in the same semester
    query = """
    MATCH (courseA)-[:ns0__hocTruoc]->(courseB)
    WHERE elementId(courseA) = $course_id AND elementId(courseB) = $target_id AND courseA.ns0__hocKy = courseB.ns0__hocKy
    RETURN courseA, courseB
    """
    params = {
        'course_id': course_id,
        'target_id': target_id
    }
    return execute_query(query, params)

def create_course(data):
    query = """
    CREATE (course:Resource:owl__NamedIndividual {
        ns0__hocKy: $ns0__hocKy,
        ns0__laMonTuChon: coalesce($ns0__laMonTuChon, false),
        ns0__maMonHoc: $ns0__maMonHoc,
        ns0__soTinChi: $ns0__soTinChi,
        rdfs__label: $rdfs__label
    })
    RETURN elementId(course) AS course_id, course
    """
    params = {
        'ns0__hocKy': data.get('ns0__hocKy'),
        'ns0__laMonTuChon': data.get('ns0__laMonTuChon'),
        'ns0__maMonHoc': data.get('ns0__maMonHoc'),
        'ns0__soTinChi': data.get('ns0__soTinChi'),
        'rdfs__label': data.get('rdfs__label')
    }
    return execute_query(query, params)

def create_relation(course_id, relation):
    query = f"""
    MATCH (course) WHERE elementId(course) = $course_id
    MATCH (target) WHERE elementId(target) = $target_id
    CREATE (course)-[:`{relation['relation_type']}`]->(target)
    """
    params = {
        'course_id': course_id,
        'target_id': relation['target_id']
    }
    execute_query(query, params)

def update_course(course_id, data):
    query = """
    MATCH (course) WHERE elementId(course) = $course_id
    SET course.ns0__hocKy = coalesce($ns0__hocKy, course.ns0__hocKy),
        course.ns0__laMonTuChon = coalesce($ns0__laMonTuChon, course.ns0__laMonTuChon),
        course.ns0__soTinChi = coalesce($ns0__soTinChi, course.ns0__soTinChi),
        course.rdfs__label = coalesce($rdfs__label, course.rdfs__label)
    RETURN elementId(course) AS course_id, course
    """
    params = {
        'course_id': course_id,
        'ns0__hocKy': data.get('ns0__hocKy'),
        'ns0__laMonTuChon': data.get('ns0__laMonTuChon'),
        'ns0__soTinChi': data.get('ns0__soTinChi'),
        'rdfs__label': data.get('rdfs__label')
    }
    return execute_query(query, params)

def update_relation(relation_id, relation_type, target_id):
    # Match the existing relation to be updated
    query = f"""
    MATCH ()-[rel]->() 
    WHERE elementId(rel) = $relation_id
    WITH rel, startNode(rel) AS start
    DELETE rel
    WITH start
    MATCH (new_target) WHERE elementId(new_target) = $target_id
    CREATE (start)-[newRel:`{relation_type}`]->(new_target)
    RETURN elementId(newRel) AS relation_id, type(newRel) AS relation_type, elementId(new_target) AS target_id
    """
    params = {
        'relation_id': relation_id,
        'relation_type': relation_type,
        'target_id': target_id
    }
    return execute_query(query, params)

# Blueprint setup
courses_bp = Blueprint('courses', __name__)

# Route functions
@courses_bp.route('/courses', methods=['POST'])
def add_course():
    data = request.get_json()
    ns0__maMonHoc = data.get('ns0__maMonHoc')

    existing_course = check_existing_course(ns0__maMonHoc)
    if existing_course:
        return jsonify({'error': f'Course with code {ns0__maMonHoc} already exists.'}), 400

    course = create_course(data)
    if not course:
        return jsonify({'error': 'Failed to create course.'}), 500

    course_data = {
        'course_id': course[0]['course_id'],
        'ns0__hocKy': course[0]['course']['ns0__hocKy'],
        'ns0__laMonTuChon': course[0]['course']['ns0__laMonTuChon'],
        'ns0__maMonHoc': course[0]['course']['ns0__maMonHoc'],
        'ns0__soTinChi': course[0]['course']['ns0__soTinChi'],
        'rdfs__label': course[0]['course']['rdfs__label']
    }

    return jsonify({'message': 'Course added successfully!', 'course': course_data}), 201

@courses_bp.route('/courses/<course_id>/relations', methods=['POST'])
def add_course_relations(course_id):
    data = request.get_json()
    relations = data.get('relations', [])
    
    for relation in relations:
        relation_type = relation.get('relation_type')
        target_id = relation.get('target_id')
        if relation_type and target_id:
            existing_target = check_existing_target(target_id)
            if not existing_target:
                return jsonify({'error': f'Target with id {target_id} does not exist.'}), 400

            # Check for prerequisite violation
            if relation_type == 'ns0__tienQuyet':
                violation = check_prerequisite_violation(course_id, target_id)
                if violation:
                    return jsonify({'error': 'Prerequisite violation: Both courses are in the same semester.'}), 400

            # Check for parallel violation
            if relation_type == 'ns0__songHanh':
                violation = check_parallel_violation(course_id, target_id)
                if violation:
                    return jsonify({'error': 'Parallel violation: Courses cannot be taken in different semesters.'}), 400

            # Check for prior violation
            if relation_type == 'ns0__hocTruoc':
                violation = check_prior_violation(course_id, target_id)
                if violation:
                    return jsonify({'error': 'Prior violation: Both courses are in the same semester.'}), 400

            existing_relation = check_existing_relation(course_id, target_id, relation_type)
            if existing_relation:
                return jsonify({'error': f'Relation {relation_type} between course {course_id} and target {target_id} already exists.'}), 400

            create_relation(course_id, relation)
    return jsonify({'message': 'Relations added successfully!'}), 201

@courses_bp.route('/courses/relations/<relation_id>', methods=['PUT'])
def update_relation_by_id(relation_id):
    data = request.get_json()
    relation_type = data.get('relation_type')
    target_id = data.get('target_id')
    
    if not relation_type or not target_id:
        return jsonify({'error': 'Missing relation_type or target_id.'}), 400

    # Check if the same relation already exists
    query_check = """
    MATCH (course)-[rel:`{relation_type}`]->(target)
    WHERE elementId(rel) <> $relation_id AND elementId(target) = $target_id
    RETURN rel
    """
    params_check = {
        'relation_id': relation_id,
        'target_id': target_id,
        'relation_type': relation_type
    }
    existing_relation = execute_query(query_check, params_check)

    if existing_relation:
        return jsonify({'error': 'Relation with the same type and target already exists, update not allowed.'}), 400

    # Check for prerequisite violation
    if relation_type == 'ns0__tienQuyet':
        violation = check_prerequisite_violation(target_id, relation_id)
        if violation:
            return jsonify({'error': 'Prerequisite violation: Both courses are in the same semester.'}), 400

    # Check for parallel violation
    if relation_type == 'ns0__songHanh':
        violation = check_parallel_violation(target_id, relation_id)
        if violation:
            return jsonify({'error': 'Parallel violation: Courses cannot be taken in different semesters.'}), 400

    # Check for prior violation
    if relation_type == 'ns0__hocTruoc':
        violation = check_prior_violation(target_id, relation_id)
        if violation:
            return jsonify({'error': 'Prior violation: Both courses are in the same semester.'}), 400
    
    updated_relation = update_relation(relation_id, relation_type, target_id)
    
    if not updated_relation:
        return jsonify({'error': 'Failed to update relation.'}), 500

    return jsonify({'message': 'Relation updated successfully!', 'relation': updated_relation}), 200

@courses_bp.route('/courses', methods=['GET'])
def get_courses():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    filter_relation = request.args.get('relation', None)
    user_id = request.args.get('user_id', None)

    count_query = """
    MATCH (ancestor:Resource {rdfs__label: 'Môn học'})
    MATCH (n:Resource)-[:rdfs__subClassOf*]->(ancestor)
    MATCH (instance:Resource)-[:rdf__type]->(n)
    RETURN count(instance) AS total_courses
    """
    total_courses_result = execute_query(count_query, {})
    total_courses = total_courses_result[0]['total_courses'] if total_courses_result else 0

    total_pages = (total_courses + limit - 1) // limit

    query = """
    MATCH (ancestor:Resource {rdfs__label: 'Môn học'})
    MATCH (n:Resource)-[:rdfs__subClassOf*]->(ancestor)
    MATCH (instance:Resource)-[:rdf__type]->(n)
    OPTIONAL MATCH (instance)-[rel]->(related)
    OPTIONAL MATCH (uc:UserCourse {user_id: $user_id, course_id: elementId(instance)})
    WITH instance, collect({relation_id: elementId(rel), relation_type: type(rel), target_id: elementId(related), rdfs__label: related.rdfs__label}) AS all_relations, uc.status AS course_status
    WHERE ($filter_relation IS NULL OR all(r IN $filter_relation WHERE any(rel IN all_relations WHERE rel.relation_type = r)))
    RETURN DISTINCT elementId(instance) AS course_id, instance.ns0__hocKy AS ns0__hocKy, instance.ns0__laMonTuChon AS ns0__laMonTuChon, instance.ns0__maMonHoc AS ns0__maMonHoc, instance.ns0__soTinChi AS ns0__soTinChi, instance.rdfs__label AS rdfs__label, [rel IN all_relations WHERE rel.rdfs__label IS NOT NULL] AS relations, course_status
    ORDER BY instance.ns0__hocKy
    SKIP $skip
    LIMIT $limit
    """
    params = {
        'filter_relation': filter_relation.split(',') if filter_relation else None,
        'user_id': user_id,
        'skip': (page - 1) * limit,
        'limit': limit
    }
    courses = execute_query(query, params)

    return jsonify({
        'total_courses': total_courses,
        'total_pages': total_pages,
        'courses': courses
    }), 200
    
@courses_bp.route('/courses/<course_id>', methods=['GET'])
def get_course_by_code(course_id):
    query = """
    MATCH (course) WHERE elementId(course) = $course_id
    OPTIONAL MATCH (course)-[rel]->(related)
    WITH course, collect({relation_id: elementId(rel), relation_type: type(rel), target_id: elementId(related), rdfs__label: related.rdfs__label}) AS relations
    RETURN elementId(course) AS course_id, course.ns0__hocKy AS ns0__hocKy, course.ns0__laMonTuChon AS ns0__laMonTuChon, course.ns0__maMonHoc AS ns0__maMonHoc, course.ns0__soTinChi AS ns0__soTinChi, course.rdfs__label AS rdfs__label, [rel IN relations WHERE rel.rdfs__label IS NOT NULL] AS relations
    """
    params = {'course_id': course_id}
    result = execute_query(query, params)
    course = result[0] if result else None

    if not course:
        return jsonify({'error': f'Course with id {course_id} not found.'}), 404

    return jsonify(course)

@courses_bp.route('/courses/<course_id>', methods=['PUT'])
def update_course_by_code(course_id):
    data = request.get_json()
    
    # Check if the course exists
    existing_course = check_existing_course(course_id)
    if not existing_course:
        return jsonify({'error': f'Course with id {course_id} does not exist.'}), 404

    # Extract the new semester value from the input data
    new_semester = data.get('ns0__hocKy')

    # If the semester is being updated, check for violations
    if new_semester is not None:
        # Check for prior (`ns0__hocTruoc`) relationship violation
        query_prior = """
        MATCH (courseA)-[:ns0__hocTruoc]->(courseB)
        WHERE elementId(courseA) = $course_id
        RETURN elementId(courseB) AS target_id, courseB.ns0__hocKy AS semesterB, courseB.rdfs__label AS labelB
        """
        params = {'course_id': course_id}
        related_courses_prior = execute_query(query_prior, params)

        # Ensure the updated semester value does not violate prior rules
        for related_course in related_courses_prior:
            if new_semester >= related_course['semesterB']:
                return jsonify({
                    'error': f'Prior relation violation: The semester of this course ({new_semester}) must be earlier than the semester of course "{related_course["labelB"]}" ({related_course["semesterB"]}).'
                }), 400

        # Check for parallel (`ns0__songHanh`) relationship violation
        query_parallel = """
        MATCH (courseA)-[:ns0__songHanh]->(courseB)
        WHERE elementId(courseA) = $course_id
        RETURN elementId(courseB) AS target_id, courseB.ns0__hocKy AS semesterB, courseB.rdfs__label AS labelB
        """
        related_courses_parallel = execute_query(query_parallel, params)

        # Ensure the updated semester value matches the semester of related courses in parallel relationships
        for related_course in related_courses_parallel:
            if new_semester != related_course['semesterB']:
                return jsonify({
                    'error': f'Parallel relation violation: The semester of this course ({new_semester}) must match the semester of course "{related_course["labelB"]}" ({related_course["semesterB"]}).'
                }), 400

        # Check for prerequisite (`ns0__tienQuyet`) relationship violation
        query_prerequisite = """
        MATCH (courseA)-[:ns0__tienQuyet]->(courseB)
        WHERE elementId(courseA) = $course_id
        RETURN elementId(courseB) AS target_id, courseB.ns0__hocKy AS semesterB, courseB.rdfs__label AS labelB
        """
        related_courses_prerequisite = execute_query(query_prerequisite, params)

        # Ensure that the prerequisite course is in an earlier semester
        for related_course in related_courses_prerequisite:
            if new_semester >= related_course['semesterB']:
                return jsonify({
                    'error': f'Prerequisite relation violation: The semester of this course ({new_semester}) must be earlier than the semester of course "{related_course["labelB"]}" ({related_course["semesterB"]}).'
                }), 400

    # Proceed to update the course
    updated_course = update_course(course_id, data)
    if not updated_course:
        return jsonify({'error': 'Failed to update the course.'}), 500

    updated_course_data = {
        'course_id': updated_course[0]['course_id'],
        'ns0__hocKy': updated_course[0]['course']['ns0__hocKy'],
        'ns0__laMonTuChon': updated_course[0]['course']['ns0__laMonTuChon'],
        'ns0__maMonHoc': updated_course[0]['course']['ns0__maMonHoc'],
        'ns0__soTinChi': updated_course[0]['course']['ns0__soTinChi'],
        'rdfs__label': updated_course[0]['course']['rdfs__label']
    }

    return jsonify({'message': 'Course updated successfully!', 'course': updated_course_data}), 200

@courses_bp.route('/courses/<course_id>', methods=['DELETE'])
def delete_course(course_id):
    existing_course = check_existing_course(course_id)
    if not existing_course:
        return jsonify({'error': f'Course with id {course_id} does not exist.'}), 404

    delete_relationships_query = """
    MATCH (course)-[rel]->()
    WHERE elementId(course) = $course_id
    DELETE rel
    """
    params = {'course_id': course_id}
    execute_query(delete_relationships_query, params)

    delete_inverse_relationships_query = """
    MATCH ()-[rel]->(course)
    WHERE elementId(course) = $course_id
    DELETE rel
    """
    execute_query(delete_inverse_relationships_query, params)

    delete_course_query = """
    MATCH (course) WHERE elementId(course) = $course_id
    DELETE course
    """
    execute_query(delete_course_query, params)

    return jsonify({'message': f'Course with id {course_id} deleted successfully, along with all its relationships.'}), 200


@courses_bp.route('/courses/<course_id>/eligible-relations', methods=['GET'])
def get_eligible_courses_for_relation(course_id):
    relation_types = ['ns0__tienQuyet', 'ns0__hocTruoc', 'ns0__songHanh']
    results = {}
    for relation_type in relation_types:
        query = f"""
        MATCH (courseA) WHERE elementId(courseA) = $course_id
        MATCH (courseB:Resource)
        WHERE elementId(courseB) <> $course_id
        """

        if relation_type == 'ns0__tienQuyet' or relation_type == 'ns0__hocTruoc':
            # Ensure courseA and courseB are in different semesters
            query += f"""
            AND courseA.ns0__hocKy > courseB.ns0__hocKy
            AND NOT (courseB)-[:{relation_type}]->(courseA)
            """
        elif relation_type == 'ns0__songHanh':
            # Ensure courseA and courseB can be taken in the same semester
            query += f"""
            AND courseA.ns0__hocKy = courseB.ns0__hocKy
            """

        query += """
        RETURN elementId(courseB) AS course_id, courseB.ns0__maMonHoc AS ns0__maMonHoc, courseB.rdfs__label AS rdfs__label
        """
        params = {
            'course_id': course_id
        }
        eligible_courses = execute_query(query, params)
        results[relation_type] = [
            {
                'course_id': course['course_id'],
                'ns0__maMonHoc': course['ns0__maMonHoc'],
                'rdfs__label': course['rdfs__label']
            }
            for course in eligible_courses
        ]

    return jsonify(results), 200