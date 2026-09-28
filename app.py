import os
from flask import Flask, render_template, request, jsonify, session
from database import init_db, create_lecture, create_user, find_user_by_username, find_user_by_email, verify_password, get_lecture_by_id, get_lectures_by_user, update_lecture, delete_lecture, create_lecture_chunks, get_lecture_chunks, create_study_pack
from services.document_processor import extract_text_from_file, is_allowed_file
from services.task_router import route_task, get_supported_tasks
from services.model_selection import select_model, get_provider_status
from services.rag_service import chunk_lecture, search_chunks, get_chunk_context, retrieve_context
from services.llm_service import generate_study_material, get_llm_service_status

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not username:
        return jsonify({"error": "Username is required"}), 400
    if not email:
        return jsonify({"error": "Email is required"}), 400
    if not password:
        return jsonify({"error": "Password is required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if find_user_by_username(username):
        return jsonify({"error": "Username already taken"}), 400
    if find_user_by_email(email):
        return jsonify({"error": "Email already registered"}), 400

    user_id = create_user(username, email, password)
    if user_id is None:
        return jsonify({"error": "Failed to create user"}), 500

    session["user_id"] = user_id
    session["username"] = username
    return jsonify({"message": "Registration successful", "user_id": user_id}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = find_user_by_username(username)
    if not user or not verify_password(user, password):
        return jsonify({"error": "Invalid username or password"}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return jsonify({"message": "Login successful", "user_id": user["id"]}), 200


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200


@app.route("/api/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"user": None}), 200
    return jsonify({"user": {"id": session["user_id"], "username": session["username"]}}), 200


@app.route("/api/lectures", methods=["POST"])
def create_lecture_endpoint():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if not content:
        return jsonify({"error": "Content is required"}), 400

    try:
        lecture_id = create_lecture(session["user_id"], title, content)

        # Chunk the lecture content for RAG
        chunks = chunk_lecture(lecture_id, content)
        create_lecture_chunks(lecture_id, chunks)

        return jsonify({
            "message": "Lecture saved successfully",
            "lecture_id": lecture_id,
            "chunks_created": len(chunks)
        }), 201
    except Exception as e:
        return jsonify({"error": "Failed to save lecture"}), 500


@app.route("/api/lectures", methods=["GET"])
def list_lectures():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    lectures = get_lectures_by_user(session["user_id"])
    return jsonify({
        "lectures": [dict(l) for l in lectures]
    }), 200


@app.route("/api/lectures/<int:lecture_id>", methods=["GET"])
def get_lecture(lecture_id):
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    lecture = get_lecture_by_id(lecture_id, session["user_id"])
    if not lecture:
        return jsonify({"error": "Lecture not found"}), 404

    return jsonify({"lecture": dict(lecture)}), 200


@app.route("/api/lectures/<int:lecture_id>", methods=["PUT"])
def update_lecture_endpoint(lecture_id):
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if not content:
        return jsonify({"error": "Content is required"}), 400

    if not update_lecture(lecture_id, session["user_id"], title, content):
        return jsonify({"error": "Lecture not found"}), 404

    return jsonify({"message": "Lecture updated successfully"}), 200


@app.route("/api/lectures/<int:lecture_id>", methods=["DELETE"])
def delete_lecture_endpoint(lecture_id):
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    if not delete_lecture(lecture_id, session["user_id"]):
        return jsonify({"error": "Lecture not found"}), 404

    return jsonify({"message": "Lecture deleted successfully"}), 200


@app.route("/api/lectures/upload", methods=["POST"])
def upload_lecture():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not is_allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Allowed: PDF, DOCX"}), 400

    title = request.form.get("title", "").strip()
    if not title:
        title = file.filename.rsplit(".", 1)[0]

    try:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            extracted_text = extract_text_from_file(tmp_path, file.filename)
        finally:
            os.unlink(tmp_path)

        if not extracted_text:
            return jsonify({"error": "Could not extract text from file (file may be empty or scanned)"}), 400

        lecture_id = create_lecture(session["user_id"], title, extracted_text)

        # Chunk the lecture content for RAG
        chunks = chunk_lecture(lecture_id, extracted_text)
        create_lecture_chunks(lecture_id, chunks)

        return jsonify({
            "message": "Lecture uploaded and text extracted successfully",
            "lecture_id": lecture_id,
            "title": title,
            "content_preview": extracted_text[:200] + ("..." if len(extracted_text) > 200 else ""),
            "chunks_created": len(chunks)
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to process upload"}), 500


@app.route("/api/tasks/route", methods=["POST"])
def route_task_endpoint():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    task_input = data.get("task", "").strip()
    lecture_id = data.get("lecture_id")

    if not task_input:
        return jsonify({"error": "Task description is required"}), 400

    if lecture_id is not None:
        lecture = get_lecture_by_id(lecture_id, session["user_id"])
        if not lecture:
            return jsonify({"error": "Lecture not found"}), 404

    result = route_task(task_input)

    response = {
        "task_type": result["task_type"],
        "confidence": result["confidence"]
    }

    if result["error"]:
        response["error"] = result["error"]
        return jsonify(response), 400

    if lecture_id is not None:
        response["lecture_id"] = lecture_id
        response["lecture_title"] = lecture["title"]

    return jsonify(response), 200


@app.route("/api/tasks/supported", methods=["GET"])
def supported_tasks_endpoint():
    return jsonify({"tasks": get_supported_tasks()}), 200


@app.route("/api/models/select", methods=["POST"])
def select_model_endpoint():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    task_type = data.get("task_type")
    preferred_provider = data.get("provider")

    if not task_type:
        return jsonify({"error": "task_type is required"}), 400

    if task_type not in {"summary", "notes", "questions", "mcqs"}:
        return jsonify({"error": f"Unsupported task_type: {task_type}"}), 400

    if preferred_provider and preferred_provider not in {"local", "huggingface"}:
        return jsonify({"error": f"Unsupported provider: {preferred_provider}"}), 400

    result = select_model(task_type, preferred_provider)

    if result["error"] and not result["available"]:
        return jsonify(result), 400

    return jsonify(result), 200


@app.route("/api/models/status", methods=["GET"])
def model_status_endpoint():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    return jsonify(get_provider_status()), 200


@app.route("/api/lectures/<int:lecture_id>/chunks", methods=["GET"])
def get_lecture_chunks_endpoint(lecture_id):
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    chunks = get_lecture_chunks(lecture_id, session["user_id"])
    if chunks is None:
        return jsonify({"error": "Lecture not found"}), 404

    return jsonify({"lecture_id": lecture_id, "chunks": chunks}), 200


@app.route("/api/rag/search", methods=["POST"])
def rag_search_endpoint():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    query = data.get("query", "").strip()
    lecture_id = data.get("lecture_id")
    top_k = data.get("top_k", 5)

    if not query:
        return jsonify({"error": "Query is required"}), 400

    if lecture_id is not None:
        # Search within a specific lecture
        lecture = get_lecture_by_id(lecture_id, session["user_id"])
        if not lecture:
            return jsonify({"error": "Lecture not found"}), 404

        chunks = get_lecture_chunks(lecture_id, session["user_id"])
        if not chunks:
            return jsonify({"lecture_id": lecture_id, "results": []}), 200

        results = search_chunks(query, chunks, top_k)
        context = get_chunk_context(results)

        return jsonify({
            "lecture_id": lecture_id,
            "lecture_title": lecture["title"],
            "query": query,
            "results": results,
            "context": context
        }), 200
    else:
        # Search across all user's lectures
        results = search_lecture_chunks(session["user_id"], query, top_k)

        return jsonify({
            "query": query,
            "results": results
        }), 200


@app.route("/api/rag/chunk/<int:lecture_id>", methods=["POST"])
def chunk_lecture_endpoint(lecture_id):
    """Manually trigger chunking for an existing lecture."""
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    lecture = get_lecture_by_id(lecture_id, session["user_id"])
    if not lecture:
        return jsonify({"error": "Lecture not found"}), 404

    chunks = chunk_lecture(lecture_id, lecture["content"])
    created = create_lecture_chunks(lecture_id, chunks)

    return jsonify({
        "lecture_id": lecture_id,
        "chunks_created": created
    }), 200


@app.route("/api/study-pack/generate", methods=["POST"])
def generate_study_pack_endpoint():
    """
    Generate study pack for a lecture using the full pipeline:
    Task Router -> Model Selection -> RAG Retrieval -> LLM Generation
    """
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    task_input = data.get("task", "").strip()
    lecture_id = data.get("lecture_id")
    provider = data.get("provider")

    if not task_input:
        return jsonify({"error": "Task description is required"}), 400
    if lecture_id is None:
        return jsonify({"error": "lecture_id is required"}), 400

    # Step 1: Verify lecture ownership
    lecture = get_lecture_by_id(lecture_id, session["user_id"])
    if not lecture:
        return jsonify({"error": "Lecture not found"}), 404

    # Step 2: Task Router - identify the task type
    route_result = route_task(task_input)
    if route_result["error"]:
        return jsonify({
            "error": route_result["error"],
            "task_type": None
        }), 400

    task_type = route_result["task_type"]

    # Step 3: Model Selection - determine provider/model
    model_result = select_model(task_type, provider)
    if model_result["error"] and not model_result["available"]:
        return jsonify(model_result), 400

    # Step 4: RAG Retrieval - get relevant lecture context
    rag_result = retrieve_context(
        lecture_id=lecture_id,
        user_id=session["user_id"],
        task_type=task_type,
        top_k=5,
        max_context_chars=3000
    )
    
    if rag_result.get("error"):
        return jsonify({"error": rag_result["error"]}), 400
    
    context = rag_result["context"]
    
    if not context:
        return jsonify({"error": "Could not retrieve relevant lecture context"}), 400

    # Step 5: LLM Generation - generate study material
    gen_result = generate_study_material(task_type, context, model_result["provider"])

    if not gen_result["success"]:
        return jsonify({
            "error": gen_result["error"],
            "task_type": task_type,
            "provider": model_result["provider"],
            "model": model_result["model"]
        }), 500

    # Save to study_packs table
    create_study_pack(lecture_id, task_type, gen_result["content"])

    # Return successful result
    return jsonify({
        "task_type": task_type,
        "lecture_id": lecture_id,
        "lecture_title": lecture["title"],
        "provider": gen_result["provider"],
        "model": gen_result["model"],
        "chunks_used": rag_result["chunks_used"],
        "fallback_used": rag_result.get("fallback_used", False),
        "content": gen_result["content"]
    }), 200


@app.route("/api/llm/status", methods=["GET"])
def llm_status_endpoint():
    """Get the status of the LLM service."""
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    return jsonify(get_llm_service_status()), 200

if __name__ == "__main__":
    app.run(debug=True)