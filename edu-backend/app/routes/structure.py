# app/routes/structure.py
from flask import Blueprint, jsonify, request
from app.utils import execute_query

# Create a blueprint for structure routes
structure_bp = Blueprint('structure', __name__)

@structure_bp.route('/structure/relations/<relation_id>', methods=['DELETE'])
def delete_relation(relation_id):
    # Cypher query to match and delete the relation with the given elementId
    query = """
    MATCH ()-[rel]->() WHERE elementId(rel) = $relation_id
    DELETE rel
    RETURN $relation_id AS deleted_relation_id
    """
    params = {'relation_id': relation_id}
    deleted_relation = execute_query(query, params)
    if not deleted_relation:
        return jsonify({'error': f'Failed to delete relation with id {relation_id}.'}), 500
    return jsonify({'message': f'Relation with id {relation_id} deleted successfully!'}), 200

@structure_bp.route('/structure/relation-types', methods=['GET'])
def get_relation_types():
    # Cypher query to get all distinct relation types in the database
    query = """
    MATCH ()-[rel]->()
    RETURN DISTINCT type(rel) AS relation_type
    """
    relation_types = execute_query(query, {})
    if not relation_types:
        return jsonify({'relation_types': []}), 200
    return jsonify({'relation_types': [rel['relation_type'] for rel in relation_types]}), 200

@structure_bp.route('/structure/ontology-classes', methods=['GET'])
def get_ontology_structure():
    # Cypher query to get class hierarchy, including parent and child classes
    query = """
    MATCH (child:Resource)-[:rdfs__subClassOf*]->(ancestor:Resource)
    RETURN DISTINCT elementId(child) AS child_id, child.rdfs__label AS child_label,
                    elementId(ancestor) AS ancestor_id, ancestor.rdfs__label AS ancestor_label
    """
    class_hierarchy = execute_query(query, {})

    # Organize the class structure into a nested dictionary
    class_structure = {}
    for record in class_hierarchy:
        child_id = record['child_id']
        child_label = record['child_label']
        ancestor_id = record['ancestor_id']
        ancestor_label = record['ancestor_label']

        # Use a tuple for ancestor_key to make it hashable
        ancestor_key = (ancestor_id, ancestor_label)
        child_info = {'child_id': child_id, 'child_label': child_label}

        if ancestor_key not in class_structure:
            class_structure[ancestor_key] = []
        class_structure[ancestor_key].append(child_info)

    # Convert dictionary keys to list for JSON serialization
    ontology_structure = [{'ancestor': {'ancestor_id': key[0], 'ancestor_label': key[1]}, 'children': value} for key, value in class_structure.items()]

    return jsonify({'ontology_structure': ontology_structure}), 200