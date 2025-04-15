from flask import Flask, request, jsonify, render_template, session
from phi.agent import Agent
from phi.model.groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-20q-key")

# Initialize the Groq Agent
agent = Agent(
    model=Groq(id="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
)

# Homepage
@app.route('/')
def index():
    return render_template('index.html')

# Chat endpoint
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip().lower()

    # System prompt for the agent
    system_prompt = (
        "You are the guesser in a game of 20 Questions. The user is thinking of an object, and you must figure it out "
        "by asking one yes-or-no question at a time. You must remember what you’ve already asked. "
        "NEVER repeat any question. Do not ask the same thing in different wording. "
        "Your questions should narrow the search intelligently. When confident, make a guess like 'Is it a banana?'."
    )

    # Restart game
    if user_input == "restart":
        session.pop("qa", None)
        return jsonify({"response": "Game restarted. Let's begin!\n\nIs it a living thing?"})

    # Start game
    if user_input == "start":
        session["qa"] = [{"question": "Is it a living thing?", "answer": None}]
        return jsonify({"response": "Is it a living thing?"})

    # Make sure game is started
    if "qa" not in session or not session["qa"]:
        return jsonify({"response": "Please type 'start' to begin the game."})

    # Save user answer
    qa = session.get("qa", [])
    if qa[-1]["answer"] is None:
        qa[-1]["answer"] = user_input
        session["qa"] = qa  # Reassign to ensure persistence
    else:
        return jsonify({"response": "Please wait for the next question. Type 'restart' if needed."})

    # Format Q&A history
    qa_lines = [f"- {item['question']} {item['answer']}" for item in qa if item["answer"]]
    question_count = len(qa_lines)
    remaining = 20 - question_count

    prompt = (
        f"You have asked {question_count} questions. You have {remaining} left.\n"
        f"These are the questions and answers so far:\n"
        f"{chr(10).join(qa_lines)}\n\nAsk your next yes/no question:"
    )

    try:
        response_obj = agent.run(prompt, system=system_prompt)
        next_question = response_obj.content.strip()

        # Prevent exact repetition
        asked_questions = [q["question"].lower() for q in qa if q.get("question")]
        if next_question.lower() in asked_questions:
            next_question += " (Try rephrasing or asking something new!)"

        qa.append({"question": next_question, "answer": None})
        session["qa"] = qa  # Save updated list
    except Exception as e:
        next_question = f"Error: {e}"

    return jsonify({"response": next_question})


if __name__ == '__main__':
    app.run(debug=True)
