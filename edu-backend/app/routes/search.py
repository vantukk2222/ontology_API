# app/routes/search.py
from flask import Blueprint, jsonify, request
from transformers import AutoTokenizer, AutoModel
import torch
import faiss
import numpy as np
import os
import unidecode

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
    "CSDL": "cơ sở dữ liệu",
    "PPT": "phương pháp tính"
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

    # Truy vấn để lấy thông tin các môn học
    query = """
      MATCH (ancestor:Resource {rdfs__label: 'Môn học'})
      MATCH (n:Resource)-[:rdfs__subClassOf*]->(ancestor)
      MATCH (instance:Resource)-[:rdf__type]->(n)
      RETURN DISTINCT instance.ns0__maMonHoc AS code, instance.rdfs__label AS label
    """
    results = execute_query(query, {})

    # Danh sách môn học và tên (bao gồm cả không dấu và có dấu)
    subjects = [(result['code'], result['label']) for result in results]
    subjects_with_unaccented = [(code, label, unidecode.unidecode(label)) for code, label in subjects]
    labels = [subject[1] for subject in subjects if subject[1]]

    # Mã hóa các môn học thành vector
    subject_vectors = [encode_sentence(subject[1], phobert_tokenizer, phobert_model) for subject in subjects]

    # Sử dụng FAISS để lập chỉ mục và tìm kiếm ngữ nghĩa
    dimension = subject_vectors[0].shape[0]
    index = faiss.IndexFlatIP(dimension)  # Sử dụng chỉ số IP để tính độ tương đồng cosine
    subject_vectors_np = np.array(subject_vectors).astype('float32')
    # Chuẩn hóa vector để tính cosine similarity
    faiss.normalize_L2(subject_vectors_np)
    index.add(subject_vectors_np)

    # Mã hóa câu truy vấn
    query_vector = encode_sentence(query_sentence, phobert_tokenizer, phobert_model).astype('float32')
    # Chuẩn hóa vector truy vấn
    faiss.normalize_L2(query_vector.reshape(1, -1))
    distances, indices = index.search(np.array([query_vector]), top_k)
    
    results = []
    seen_labels = set()
    for i, idx in enumerate(indices[0]):
        label = labels[idx]
        code = subjects[idx][0]
        
        if label not in seen_labels:
            results.append({'label': label, 'code': code, 'score': float(distances[0][i])})
            seen_labels.add(label)
    
    # Sắp xếp kết quả theo điểm số từ cao đến thấp
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    return jsonify({'results': results}), 200
