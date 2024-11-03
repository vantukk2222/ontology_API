# app/routes/search.py
from flask import Blueprint, jsonify, request
from transformers import AutoTokenizer, AutoModel
import torch
import faiss
import numpy as np
import os

from app.utils import execute_query

# Create a blueprint for search routes
search_bp = Blueprint('search', __name__)

# Từ điển từ viết tắt và từ đồng nghĩa
abbreviation_dict = {
    "HTTT": "hệ thống thông tin",
    "CNPM": "công nghệ phần mềm",
    "ATTT": "an toàn thông tin",
    "CNTT": "công nghệ thông tin",
    "AI": "trí tuệ nhân tạo",
    "CSDL": "cơ sở dữ liệu"
}

# Khởi tạo PhoBERT
phobert_tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base", use_fast=False)
phobert_model = AutoModel.from_pretrained("vinai/phobert-base")

def encode_sentence(sentence, tokenizer, model):
    """
    Mã hóa câu sử dụng PhoBERT và trả về vector ngữ nghĩa
    """
    # Thay thế từ viết tắt bằng nghĩa đầy đủ
    for abbr, full_form in abbreviation_dict.items():
        sentence = sentence.replace(abbr, full_form)
    
    tokens = tokenizer.encode(sentence, return_tensors='pt', truncation=True, max_length=128)
    with torch.no_grad():
        output = model(tokens)
    
    return output.last_hidden_state.mean(dim=1).squeeze().numpy()

@search_bp.route('/search', methods=['GET'])
def search_ontology_classes():
    
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    # Lấy câu truy vấn từ request
    query_sentence = request.args.get('query', None)
    top_k = int(request.args.get('top_k', 5))

    if not query_sentence:
        return jsonify({'error': 'Missing query parameter.'}), 400

    # Thay thế từ viết tắt trong câu truy vấn
    for abbr, full_form in abbreviation_dict.items():
        query_sentence = query_sentence.replace(abbr, full_form)

    # Truy vấn để lấy thông tin các môn học và các lớp liên quan
    query = """
      MATCH (ancestor:Resource {rdfs__label: 'Môn học'})
      MATCH (n:Resource)-[:rdfs__subClassOf*]->(ancestor)
      MATCH (instance:Resource)-[:rdf__type]->(n)
      RETURN DISTINCT instance.ns0__maMonHoc AS code, instance.rdfs__label AS label, n.rdfs__label AS class_label
    """
    results = execute_query(query, {})

    # Danh sách môn học và tên
    subjects = [(result['code'], result['label'], result['class_label']) for result in results]
    labels = [subject[1] for subject in subjects if subject[1]]

    # Mã hóa các môn học thành vector
    subject_vectors = []
    for subject in subjects:
        label = subject[1]
        class_label = subject[2]
        code = subject[0]
        # Gán trọng số cao hơn cho nhãn môn học và lớp môn học
        weighted_description = f"{label} " * 4 + f"{class_label} " * 3
        vector = encode_sentence(weighted_description, phobert_tokenizer, phobert_model)
        subject_vectors.append(vector)

    # Sử dụng FAISS để lập chỉ mục và tìm kiếm ngữ nghĩa
    dimension = subject_vectors[0].shape[0]
    index = faiss.IndexFlatIP(dimension)  # Sử dụng chỉ số IP để tính độ tương đồng cosine
    subject_vectors_np = np.array(subject_vectors).astype('float32')
    index.add(subject_vectors_np)

    # Tìm kiếm ngữ nghĩa
    query_vector = encode_sentence(query_sentence, phobert_tokenizer, phobert_model).astype('float32')
    distances, indices = index.search(np.array([query_vector]), top_k)
    
    results = []
    seen_labels = set()
    for i, idx in enumerate(indices[0]):
        label = labels[idx]
        code = subjects[idx][0]
        
        if label not in seen_labels:
            results.append({'label': label, 'score': float(distances[0][i])})
            seen_labels.add(label)
    
    return jsonify({'results': results}), 200
